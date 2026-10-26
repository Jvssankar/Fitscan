import json
from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from extensions import db


class User(UserMixin, db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(200), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    resumes = db.relationship("Resume", backref="user", cascade="all, delete-orphan")
    interviews = db.relationship("InterviewSession", backref="user", cascade="all, delete-orphan")

    def set_password(self, pw):
        self.password_hash = generate_password_hash(pw)

    def check_password(self, pw):
        return check_password_hash(self.password_hash, pw)


class Resume(db.Model):
    __tablename__ = "resumes"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    original_filename = db.Column(db.String(255))
    text = db.Column(db.Text, nullable=False)
    tailored_text = db.Column(db.Text, nullable=True)
    skills_json = db.Column(db.Text, default="[]")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    scans = db.relationship("ScanHistory", backref="resume", cascade="all, delete-orphan")
    job_matches = db.relationship("JobMatch", backref="resume", cascade="all, delete-orphan")

    @property
    def skills(self):
        try:
            return json.loads(self.skills_json or "[]")
        except Exception:
            return []

    @skills.setter
    def skills(self, value):
        self.skills_json = json.dumps(value or [])


class ScanHistory(db.Model):
    __tablename__ = "scan_history"
    id = db.Column(db.Integer, primary_key=True)
    resume_id = db.Column(db.Integer, db.ForeignKey("resumes.id"), nullable=False)
    mode = db.Column(db.String(20), nullable=False)
    ats_score = db.Column(db.Integer, nullable=False)
    verdict = db.Column(db.String(80))
    summary = db.Column(db.Text)
    result_json = db.Column(db.Text, nullable=False)
    jd_snippet = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    @property
    def result(self):
        return json.loads(self.result_json)

    def to_dict(self):
        return {
            "id": self.id,
            "resume_id": self.resume_id,
            "resume_filename": self.resume.original_filename if self.resume else "",
            "mode": self.mode,
            "ats_score": self.ats_score,
            "verdict": self.verdict,
            "summary": self.summary,
            "jd_snippet": self.jd_snippet,
            "created_at": self.created_at.strftime("%d %b %Y, %I:%M %p"),
        }


class JobMatch(db.Model):
    __tablename__ = "job_matches"
    __table_args__ = (db.UniqueConstraint("resume_id", "url", name="uq_resume_job_url"),)

    id = db.Column(db.Integer, primary_key=True)
    resume_id = db.Column(db.Integer, db.ForeignKey("resumes.id"), nullable=False)
    title = db.Column(db.String(300))
    company = db.Column(db.String(200))
    location = db.Column(db.String(200))
    url = db.Column(db.String(1000), nullable=False)
    source = db.Column(db.String(60))
    match_score = db.Column(db.Integer, default=0)
    matched_skills_json = db.Column(db.Text, default="[]")
    tags_json = db.Column(db.Text, default="[]")
    posted_at = db.Column(db.String(80), nullable=True)
    found_at = db.Column(db.DateTime, default=datetime.utcnow)
    # contact info
    hr_email = db.Column(db.String(200), nullable=True)
    hr_linkedin = db.Column(db.String(500), nullable=True)

    applications = db.relationship("ApplicationTracker", backref="job", cascade="all, delete-orphan")

    @property
    def matched_skills(self):
        try:
            return json.loads(self.matched_skills_json or "[]")
        except Exception:
            return []

    @matched_skills.setter
    def matched_skills(self, value):
        self.matched_skills_json = json.dumps(value or [])

    @property
    def tags(self):
        try:
            return json.loads(self.tags_json or "[]")
        except Exception:
            return []

    @tags.setter
    def tags(self, value):
        self.tags_json = json.dumps(value or [])

    def to_dict(self):
        app = self.applications[0] if self.applications else None
        return {
            "id": self.id,
            "title": self.title,
            "company": self.company,
            "location": self.location,
            "url": self.url,
            "source": self.source,
            "match_score": self.match_score,
            "matched_skills": self.matched_skills,
            "tags": self.tags,
            "posted_at": self.posted_at or "—",
            "found_at": self.found_at.strftime("%d %b %Y"),
            "hr_email": self.hr_email or "",
            "hr_linkedin": self.hr_linkedin or "",
            "application_status": app.status if app else "not_applied",
            "application_id": app.id if app else None,
        }


class ApplicationTracker(db.Model):
    __tablename__ = "applications"
    id = db.Column(db.Integer, primary_key=True)
    job_id = db.Column(db.Integer, db.ForeignKey("job_matches.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    status = db.Column(db.String(30), default="applied")
    # applied | pending | interview | rejected | offer
    applied_at = db.Column(db.DateTime, default=datetime.utcnow)
    notes = db.Column(db.Text, nullable=True)
    follow_up_at = db.Column(db.DateTime, nullable=True)

    def to_dict(self):
        j = self.job
        return {
            "id": self.id,
            "job_id": self.job_id,
            "title": j.title if j else "",
            "company": j.company if j else "",
            "url": j.url if j else "",
            "hr_email": j.hr_email if j else "",
            "match_score": j.match_score if j else 0,
            "status": self.status,
            "applied_at": self.applied_at.strftime("%d %b %Y"),
            "notes": self.notes or "",
            "follow_up_at": self.follow_up_at.strftime("%d %b %Y") if self.follow_up_at else "",
        }


class InterviewSession(db.Model):
    __tablename__ = "interview_sessions"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    resume_id = db.Column(db.Integer, db.ForeignKey("resumes.id"), nullable=True)
    job_title = db.Column(db.String(300))
    job_description = db.Column(db.Text)
    questions_json = db.Column(db.Text, default="[]")
    answers_json = db.Column(db.Text, default="[]")
    evaluation_json = db.Column(db.Text, nullable=True)
    overall_score = db.Column(db.Integer, nullable=True)
    status = db.Column(db.String(20), default="pending")
    # pending | in_progress | completed
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime, nullable=True)

    @property
    def questions(self):
        try:
            return json.loads(self.questions_json or "[]")
        except Exception:
            return []

    @questions.setter
    def questions(self, v):
        self.questions_json = json.dumps(v or [])

    @property
    def answers(self):
        try:
            return json.loads(self.answers_json or "[]")
        except Exception:
            return []

    @answers.setter
    def answers(self, v):
        self.answers_json = json.dumps(v or [])

    @property
    def evaluation(self):
        try:
            return json.loads(self.evaluation_json or "{}")
        except Exception:
            return {}

    @evaluation.setter
    def evaluation(self, v):
        self.evaluation_json = json.dumps(v or {})

    def to_dict(self):
        return {
            "id": self.id,
            "job_title": self.job_title,
            "overall_score": self.overall_score,
            "status": self.status,
            "created_at": self.created_at.strftime("%d %b %Y, %I:%M %p"),
            "completed_at": self.completed_at.strftime("%d %b %Y, %I:%M %p") if self.completed_at else None,
            "question_count": len(self.questions),
        }
