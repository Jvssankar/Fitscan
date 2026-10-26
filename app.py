import json, logging
from datetime import datetime, timedelta
from flask import Flask, jsonify, request, send_from_directory, session
from flask_login import login_user, logout_user, login_required, current_user

from config import Config
from extensions import db, login_manager
from models import User, Resume, ScanHistory, JobMatch, ApplicationTracker, InterviewSession
from services.extractor import extract_text
from services.analyzer import extract_skills, run_general_scan, run_match_scan, tailor_resume
from services.refresh import refresh_jobs_for_resume, refresh_all
from services.interview import generate_questions, evaluate_answer, generate_final_report

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s — %(message)s")
logger = logging.getLogger(__name__)

def create_app():
    app = Flask(__name__, static_folder="static", template_folder="templates")
    app.config.from_object(Config)
    db.init_app(app)
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(uid):
        return db.session.get(User, int(uid))

    with app.app_context():
        db.create_all()

    # ── Pages ────────────────────────────────────────────────────────────────
    @app.route("/")
    def index():
        return send_from_directory("templates", "index.html")

    @app.route("/login")
    def login_page():
        return send_from_directory("templates", "auth.html")

    @app.route("/register")
    def register_page():
        return send_from_directory("templates", "auth.html")

    # ── Auth API ─────────────────────────────────────────────────────────────
    @app.route("/api/auth/register", methods=["POST"])
    def register():
        d = request.get_json(silent=True) or {}
        name = (d.get("name") or "").strip()
        email = (d.get("email") or "").strip().lower()
        pw = (d.get("password") or "").strip()
        if not name or not email or not pw:
            return jsonify(error="Name, email and password are required."), 400
        if len(pw) < 6:
            return jsonify(error="Password must be at least 6 characters."), 400
        if User.query.filter_by(email=email).first():
            return jsonify(error="An account with this email already exists."), 409
        u = User(name=name, email=email)
        u.set_password(pw)
        db.session.add(u)
        db.session.commit()
        login_user(u, remember=True)
        return jsonify(ok=True, user={"id":u.id,"name":u.name,"email":u.email})

    @app.route("/api/auth/login", methods=["POST"])
    def login():
        d = request.get_json(silent=True) or {}
        email = (d.get("email") or "").strip().lower()
        pw = (d.get("password") or "").strip()
        u = User.query.filter_by(email=email).first()
        if not u or not u.check_password(pw):
            return jsonify(error="Invalid email or password."), 401
        login_user(u, remember=True)
        return jsonify(ok=True, user={"id":u.id,"name":u.name,"email":u.email})

    @app.route("/api/auth/logout", methods=["POST"])
    @login_required
    def logout():
        logout_user()
        return jsonify(ok=True)

    @app.route("/api/auth/me")
    def me():
        if current_user.is_authenticated:
            return jsonify(authenticated=True, user={"id":current_user.id,"name":current_user.name,"email":current_user.email})
        return jsonify(authenticated=False)

    # ── Resume ───────────────────────────────────────────────────────────────
    @app.route("/api/upload", methods=["POST"])
    @login_required
    def upload():
        if "file" not in request.files:
            return jsonify(error="No file provided."), 400
        f = request.files["file"]
        if not f.filename:
            return jsonify(error="Empty filename."), 400
        try:
            text = extract_text(f)
        except ValueError as e:
            return jsonify(error=str(e)), 422
        except Exception as e:
            return jsonify(error=f"Could not read file: {e}"), 500
        if len(text.strip()) < 30:
            return jsonify(error="Extracted text too short."), 422
        skills = extract_skills(text)
        r = Resume(user_id=current_user.id, original_filename=f.filename, text=text)
        r.skills = skills
        db.session.add(r)
        db.session.commit()
        try:
            refresh_jobs_for_resume(r)
        except Exception as e:
            logger.warning("Initial job refresh failed: %s", e)
        return jsonify(id=r.id, filename=r.original_filename, word_count=len(text.split()), skills=skills)

    @app.route("/api/resumes")
    @login_required
    def list_resumes():
        rs = Resume.query.filter_by(user_id=current_user.id).order_by(Resume.created_at.desc()).all()
        return jsonify([{"id":r.id,"filename":r.original_filename,"word_count":len(r.text.split()),"skills":r.skills[:10],"created_at":r.created_at.strftime("%d %b %Y, %I:%M %p"),"scan_count":len(r.scans),"job_count":len(r.job_matches),"has_tailored":bool(r.tailored_text)} for r in rs])

    @app.route("/api/resumes/<int:rid>", methods=["DELETE"])
    @login_required
    def del_resume(rid):
        r = Resume.query.filter_by(id=rid, user_id=current_user.id).first_or_404()
        db.session.delete(r); db.session.commit()
        return jsonify(ok=True)

    # ── Scans ────────────────────────────────────────────────────────────────
    @app.route("/api/scan/general", methods=["POST"])
    @login_required
    def scan_general():
        d = request.get_json(silent=True) or {}
        r = Resume.query.filter_by(id=d.get("resume_id"), user_id=current_user.id).first()
        if not r: return jsonify(error="Resume not found."), 404
        try:
            result = run_general_scan(r.text)
        except Exception as e:
            return jsonify(error=f"Scan failed: {e}"), 500
        sc = ScanHistory(resume_id=r.id, mode="general", ats_score=result.get("atsScore",0), verdict=result.get("verdict",""), summary=result.get("summary",""), result_json=json.dumps(result))
        db.session.add(sc)
        if result.get("_skills"): r.skills = result["_skills"]
        db.session.commit()
        return jsonify(scan_id=sc.id, result=result)

    @app.route("/api/scan/match", methods=["POST"])
    @login_required
    def scan_match():
        d = request.get_json(silent=True) or {}
        r = Resume.query.filter_by(id=d.get("resume_id"), user_id=current_user.id).first()
        if not r: return jsonify(error="Resume not found."), 404
        jd = (d.get("jd_text") or "").strip()
        if not jd: return jsonify(error="jd_text required."), 400
        try:
            result = run_match_scan(r.text, jd)
        except Exception as e:
            return jsonify(error=f"Scan failed: {e}"), 500
        sc = ScanHistory(resume_id=r.id, mode="match", ats_score=result.get("atsScore",0), verdict=result.get("verdict",""), summary=result.get("summary",""), result_json=json.dumps(result), jd_snippet=jd[:300])
        db.session.add(sc)
        if result.get("_skills"): r.skills = result["_skills"]
        db.session.commit()
        return jsonify(scan_id=sc.id, result=result)

    # ── Tailor ───────────────────────────────────────────────────────────────
    @app.route("/api/tailor", methods=["POST"])
    @login_required
    def tailor():
        d = request.get_json(silent=True) or {}
        r = Resume.query.filter_by(id=d.get("resume_id"), user_id=current_user.id).first()
        if not r: return jsonify(error="Resume not found."), 404
        jd = (d.get("jd_text") or "").strip()
        if not jd: return jsonify(error="jd_text required."), 400
        try:
            report = tailor_resume(r.text, jd)
            r.tailored_text = report["tailored_text"]
            db.session.commit()
        except Exception as e:
            return jsonify(error=f"Tailoring failed: {e}"), 500
        return jsonify(report)

    # ── History ──────────────────────────────────────────────────────────────
    @app.route("/api/history")
    @login_required
    def history():
        resume_ids = [r.id for r in Resume.query.filter_by(user_id=current_user.id).all()]
        scans = ScanHistory.query.filter(ScanHistory.resume_id.in_(resume_ids)).order_by(ScanHistory.created_at.desc()).limit(100).all()
        return jsonify([s.to_dict() for s in scans])

    @app.route("/api/history/<int:sid>")
    @login_required
    def get_scan(sid):
        sc = db.session.get(ScanHistory, sid)
        if not sc: return jsonify(error="Not found"), 404
        return jsonify({**sc.to_dict(), "result": sc.result})

    @app.route("/api/history/<int:sid>", methods=["DELETE"])
    @login_required
    def del_scan(sid):
        sc = db.session.get(ScanHistory, sid)
        if not sc: return jsonify(error="Not found"), 404
        db.session.delete(sc); db.session.commit()
        return jsonify(ok=True)

    # ── Jobs ─────────────────────────────────────────────────────────────────
    @app.route("/api/jobs/<int:rid>")
    @login_required
    def get_jobs(rid):
        r = Resume.query.filter_by(id=rid, user_id=current_user.id).first_or_404()
        sort = request.args.get("sort","score")
        q = JobMatch.query.filter_by(resume_id=rid)
        q = q.order_by(JobMatch.match_score.desc()) if sort=="score" else q.order_by(JobMatch.found_at.desc())
        jobs = q.limit(200).all()
        user_app_ids = {a.job_id: a for a in ApplicationTracker.query.filter_by(user_id=current_user.id).all()}
        result = []
        for j in jobs:
            d = j.to_dict()
            app = user_app_ids.get(j.id)
            d["application_status"] = app.status if app else "not_applied"
            d["application_id"] = app.id if app else None
            result.append(d)
        return jsonify({"resume_id":rid,"resume_filename":r.original_filename,"last_refreshed":r.created_at.strftime("%d %b %Y, %I:%M %p"),"total":len(result),"jobs":result})

    @app.route("/api/refresh", methods=["POST"])
    def trigger_refresh():
        secret = request.headers.get("X-Refresh-Secret","")
        if secret != Config.REFRESH_SECRET:
            return jsonify(error="Unauthorized."), 401
        results = refresh_all()
        return jsonify(ok=True, results=results)

    @app.route("/api/refresh/<int:rid>", methods=["POST"])
    @login_required
    def refresh_one(rid):
        r = Resume.query.filter_by(id=rid, user_id=current_user.id).first_or_404()
        try:
            n = refresh_jobs_for_resume(r)
            return jsonify(ok=True, new_jobs=n)
        except Exception as e:
            return jsonify(error=str(e)), 500

    # ── Applications ─────────────────────────────────────────────────────────
    @app.route("/api/apply", methods=["POST"])
    @login_required
    def apply():
        d = request.get_json(silent=True) or {}
        job_id = d.get("job_id")
        j = db.session.get(JobMatch, job_id)
        if not j: return jsonify(error="Job not found."), 404
        existing = ApplicationTracker.query.filter_by(job_id=job_id, user_id=current_user.id).first()
        if existing:
            return jsonify(ok=True, application_id=existing.id, status=existing.status, already_applied=True)
        follow_up = datetime.utcnow() + timedelta(days=7)
        app_rec = ApplicationTracker(job_id=job_id, user_id=current_user.id, status="applied", follow_up_at=follow_up)
        db.session.add(app_rec); db.session.commit()
        return jsonify(ok=True, application_id=app_rec.id, status="applied", follow_up_date=follow_up.strftime("%d %b %Y"))

    @app.route("/api/applications")
    @login_required
    def list_applications():
        apps = ApplicationTracker.query.filter_by(user_id=current_user.id).order_by(ApplicationTracker.applied_at.desc()).all()
        return jsonify([a.to_dict() for a in apps])

    @app.route("/api/applications/<int:aid>", methods=["PATCH"])
    @login_required
    def update_application(aid):
        a = ApplicationTracker.query.filter_by(id=aid, user_id=current_user.id).first_or_404()
        d = request.get_json(silent=True) or {}
        if "status" in d: a.status = d["status"]
        if "notes" in d: a.notes = d["notes"]
        db.session.commit()
        return jsonify(ok=True, status=a.status)

    # ── Interview ─────────────────────────────────────────────────────────────
    @app.route("/api/interview/start", methods=["POST"])
    @login_required
    def interview_start():
        d = request.get_json(silent=True) or {}
        job_title = (d.get("job_title") or "").strip()
        jd_text = (d.get("jd_text") or "").strip()
        resume_id = d.get("resume_id")
        if not job_title or not jd_text:
            return jsonify(error="job_title and jd_text are required."), 400
        resume_text = ""
        if resume_id:
            r = Resume.query.filter_by(id=resume_id, user_id=current_user.id).first()
            if r: resume_text = r.text
        if not Config.ANTHROPIC_API_KEY:
            return jsonify(error="ANTHROPIC_API_KEY not configured. Add it to your .env file."), 503
        try:
            questions = generate_questions(job_title, jd_text, resume_text, total=10)
        except Exception as e:
            return jsonify(error=f"Could not generate questions: {e}"), 500
        iv = InterviewSession(user_id=current_user.id, resume_id=resume_id, job_title=job_title, job_description=jd_text, status="in_progress")
        iv.questions = questions
        db.session.add(iv); db.session.commit()
        return jsonify(interview_id=iv.id, questions=questions, job_title=job_title)

    @app.route("/api/interview/<int:iid>/submit", methods=["POST"])
    @login_required
    def interview_submit(iid):
        iv = InterviewSession.query.filter_by(id=iid, user_id=current_user.id).first_or_404()
        d = request.get_json(silent=True) or {}
        answers = d.get("answers", [])
        questions = iv.questions
        if len(answers) != len(questions):
            return jsonify(error="Answer count mismatch."), 400
        evaluations = []
        for q, a in zip(questions, answers):
            ev = evaluate_answer(q, a, iv.job_title)
            evaluations.append(ev)
        try:
            report = generate_final_report(iv.job_title, questions, answers, evaluations)
        except Exception as e:
            logger.error("Report generation failed: %s", e)
            scores = [e.get("score",0) for e in evaluations if isinstance(e,dict)]
            report = {"overall_score":int(sum(scores)/max(len(scores),1)*10),"overall_grade":"C","readiness":"Review needed","executive_summary":"Interview completed.","top_strengths":[],"critical_gaps":[],"study_plan":[],"interview_tips":[]}
        iv.answers = answers
        iv.evaluation = {"evaluations": evaluations, "report": report}
        iv.overall_score = report.get("overall_score", 0)
        iv.status = "completed"
        iv.completed_at = datetime.utcnow()
        db.session.commit()
        return jsonify(ok=True, report=report, evaluations=evaluations, interview_id=iv.id)

    @app.route("/api/interview/history")
    @login_required
    def interview_history():
        ivs = InterviewSession.query.filter_by(user_id=current_user.id).order_by(InterviewSession.created_at.desc()).all()
        return jsonify([iv.to_dict() for iv in ivs])

    @app.route("/api/interview/<int:iid>")
    @login_required
    def get_interview(iid):
        iv = InterviewSession.query.filter_by(id=iid, user_id=current_user.id).first_or_404()
        return jsonify({**iv.to_dict(), "questions":iv.questions, "answers":iv.answers, "evaluation":iv.evaluation})

    @app.route("/health")
    def health():
        return jsonify(status="ok", time=datetime.utcnow().isoformat())

    return app

app = create_app()

if __name__ == "__main__":
    app.run(debug=True, port=5000)
