import logging
from datetime import datetime
from extensions import db
from models import Resume, JobMatch
from services.job_fetcher import fetch_all_jobs

logger = logging.getLogger(__name__)

def refresh_jobs_for_resume(resume):
    skills = resume.skills
    if not skills:
        return 0
    jobs = fetch_all_jobs(skills, min_score=50)
    new_count = 0
    for job in jobs:
        url = (job.get("url") or "").strip()
        if not url:
            continue
        existing = JobMatch.query.filter_by(resume_id=resume.id, url=url).first()
        if existing:
            existing.match_score = job["match_score"]
            existing.matched_skills = job["matched_skills"]
        else:
            m = JobMatch(
                resume_id=resume.id,
                title=job["title"], company=job["company"],
                location=job["location"], url=url,
                source=job["source"], match_score=job["match_score"],
                posted_at=job.get("posted_at"),
                found_at=datetime.utcnow(),
                hr_email=job.get("hr_email",""),
                hr_linkedin=job.get("hr_linkedin",""),
            )
            m.matched_skills = job["matched_skills"]
            m.tags = job.get("tags",[])
            db.session.add(m)
            new_count += 1
    db.session.commit()
    return new_count

def refresh_all():
    resumes = Resume.query.all()
    results = {}
    for r in resumes:
        try:
            n = refresh_jobs_for_resume(r)
            results[r.id] = {"status":"ok","new_jobs":n,"file":r.original_filename}
        except Exception as e:
            results[r.id] = {"status":"error","error":str(e),"file":r.original_filename}
            logger.error("Resume %d failed: %s", r.id, e)
    return results
