import re, time, logging, requests, feedparser
from datetime import datetime, timezone

logger = logging.getLogger(__name__)
HEADERS = {"User-Agent": "FitScan/2.0 (resume-matcher; educational project)"}
TIMEOUT = 15

HR_CONTACT_MAP = {
    "google": {"email": "careers@google.com", "linkedin": "https://www.linkedin.com/company/google/jobs/"},
    "microsoft": {"email": "careers@microsoft.com", "linkedin": "https://www.linkedin.com/company/microsoft/jobs/"},
    "amazon": {"email": "amazon-jobs@amazon.com", "linkedin": "https://www.linkedin.com/company/amazon/jobs/"},
    "meta": {"email": "recruiting@meta.com", "linkedin": "https://www.linkedin.com/company/meta/jobs/"},
    "apple": {"email": "jobs@apple.com", "linkedin": "https://www.linkedin.com/company/apple/jobs/"},
    "netflix": {"email": "jobs@netflix.com", "linkedin": "https://www.linkedin.com/company/netflix/jobs/"},
    "uber": {"email": "recruiting@uber.com", "linkedin": "https://www.linkedin.com/company/uber-com/jobs/"},
    "airbnb": {"email": "jobs@airbnb.com", "linkedin": "https://www.linkedin.com/company/airbnb/jobs/"},
    "twitter": {"email": "jobs@twitter.com", "linkedin": "https://www.linkedin.com/company/twitter/jobs/"},
    "linkedin": {"email": "talent@linkedin.com", "linkedin": "https://www.linkedin.com/company/linkedin/jobs/"},
    "salesforce": {"email": "recruiting@salesforce.com", "linkedin": "https://www.linkedin.com/company/salesforce/jobs/"},
    "adobe": {"email": "jobs@adobe.com", "linkedin": "https://www.linkedin.com/company/adobe/jobs/"},
    "oracle": {"email": "talent@oracle.com", "linkedin": "https://www.linkedin.com/company/oracle/jobs/"},
    "ibm": {"email": "jobs@ibm.com", "linkedin": "https://www.linkedin.com/company/ibm/jobs/"},
    "infosys": {"email": "careers@infosys.com", "linkedin": "https://www.linkedin.com/company/infosys/jobs/"},
    "wipro": {"email": "careers@wipro.com", "linkedin": "https://www.linkedin.com/company/wipro/jobs/"},
    "tcs": {"email": "careers@tcs.com", "linkedin": "https://www.linkedin.com/company/tata-consultancy-services/jobs/"},
    "accenture": {"email": "careers@accenture.com", "linkedin": "https://www.linkedin.com/company/accenture/jobs/"},
    "deloitte": {"email": "recruiting@deloitte.com", "linkedin": "https://www.linkedin.com/company/deloitte/jobs/"},
    "pwc": {"email": "careers@pwc.com", "linkedin": "https://www.linkedin.com/company/pwc/jobs/"},
    "shopify": {"email": "jobs@shopify.com", "linkedin": "https://www.linkedin.com/company/shopify/jobs/"},
    "stripe": {"email": "jobs@stripe.com", "linkedin": "https://www.linkedin.com/company/stripe/jobs/"},
    "twilio": {"email": "jobs@twilio.com", "linkedin": "https://www.linkedin.com/company/twilio/jobs/"},
    "atlassian": {"email": "jobs@atlassian.com", "linkedin": "https://www.linkedin.com/company/atlassian/jobs/"},
    "github": {"email": "jobs@github.com", "linkedin": "https://www.linkedin.com/company/github/jobs/"},
}

def _get_hr(company: str):
    if not company:
        return "", ""
    co = company.lower().strip()
    for key, info in HR_CONTACT_MAP.items():
        if key in co:
            return info["email"], info["linkedin"]
    domain = re.sub(r'[^a-z0-9]', '', co[:20])
    if domain:
        return f"careers@{domain}.com", f"https://www.linkedin.com/company/{domain}/jobs/"
    return "", ""

def _safe_get(url, params=None, retries=2):
    for i in range(retries+1):
        try:
            r = requests.get(url, params=params, headers=HEADERS, timeout=TIMEOUT)
            r.raise_for_status(); return r.json()
        except Exception as e:
            if i==retries: logger.warning("Fetch failed %s: %s", url, e); return None
            time.sleep(1.5)

def _score(skills, text):
    if not skills or not text: return 0, []
    tl = text.lower()
    m = [s for s in skills if s and re.search(r'\b'+re.escape(s)+r'\b', tl)]
    return min(100, int(len(m)/max(len(skills),1)*100)), m[:8]

def _c(s): return str(s or "").strip()
def _today(): return datetime.now(timezone.utc).strftime("%d %b %Y")

def _remoteok(skills):
    data = _safe_get("https://remoteok.com/api")
    if not data or not isinstance(data, list): return []
    out = []
    for it in data[1:]:
        if not isinstance(it, dict): continue
        hay = " ".join([_c(it.get("position")), _c(it.get("company")), _c(it.get("description","")), " ".join(it.get("tags",[]))])
        sc, ms = _score(skills, hay)
        url = _c(it.get("url") or it.get("apply_url",""))
        if not url: continue
        co = _c(it.get("company"))
        em, li = _get_hr(co)
        out.append({"title":_c(it.get("position")) or "Untitled","company":co or "Unknown","location":"Remote","url":url,"source":"RemoteOK","match_score":sc,"matched_skills":ms,"tags":it.get("tags",[])[:6],"posted_at":_c(it.get("date") or _today()),"hr_email":em,"hr_linkedin":li})
    return out

def _arbeitnow(skills):
    data = _safe_get("https://www.arbeitnow.com/api/job-board-api")
    if not data: return []
    out = []
    for it in data.get("data",[]):
        hay = " ".join([_c(it.get("title")), _c(it.get("company_name")), _c(it.get("description","")), " ".join(it.get("tags",[]))])
        sc, ms = _score(skills, hay)
        url = _c(it.get("url",""))
        if not url: continue
        co = _c(it.get("company_name"))
        em, li = _get_hr(co)
        loc = "Remote" if it.get("remote") else _c(it.get("location","Europe"))
        out.append({"title":_c(it.get("title")) or "Untitled","company":co or "Unknown","location":loc,"url":url,"source":"Arbeitnow","match_score":sc,"matched_skills":ms,"tags":it.get("tags",[])[:6],"posted_at":_c(it.get("created_at") or _today()),"hr_email":em,"hr_linkedin":li})
    return out

def _jobicy(skills):
    data = _safe_get("https://jobicy.com/api/v2/remote-jobs", params={"count":50})
    if not data: return []
    out = []
    for it in data.get("jobs",[]):
        hay = " ".join([_c(it.get("jobTitle")), _c(it.get("companyName")), _c(it.get("jobDescription","")), _c(it.get("jobIndustry",""))])
        sc, ms = _score(skills, hay)
        url = _c(it.get("url",""))
        if not url: continue
        co = _c(it.get("companyName"))
        em, li = _get_hr(co)
        out.append({"title":_c(it.get("jobTitle")) or "Untitled","company":co or "Unknown","location":_c(it.get("jobGeo") or "Remote"),"url":url,"source":"Jobicy","match_score":sc,"matched_skills":ms,"tags":[],"posted_at":_c(it.get("pubDate") or _today()),"hr_email":em,"hr_linkedin":li})
    return out

def _themuse(skills):
    data = _safe_get("https://www.themuse.com/api/public/jobs", params={"page":0})
    if not data: return []
    out = []
    for it in data.get("results",[]):
        cats = [c.get("name","") for c in it.get("categories",[])]
        locs = [l.get("name","") for l in it.get("locations",[])]
        hay = " ".join([_c(it.get("name")), _c(it.get("company",{}).get("name","")), _c(it.get("contents","")), " ".join(cats)])
        sc, ms = _score(skills, hay)
        url = _c(it.get("refs",{}).get("landing_page",""))
        if not url: continue
        co = _c(it.get("company",{}).get("name",""))
        em, li = _get_hr(co)
        out.append({"title":_c(it.get("name")) or "Untitled","company":co or "Unknown","location":", ".join(locs) if locs else "Various","url":url,"source":"The Muse","match_score":sc,"matched_skills":ms,"tags":cats[:4],"posted_at":_c(it.get("publication_date") or _today()),"hr_email":em,"hr_linkedin":li})
    return out

def _remotive(skills):
    try:
        feed = feedparser.parse("https://remotive.com/remote-jobs/feed/")
        out = []
        for e in feed.entries[:60]:
            hay = " ".join([_c(getattr(e,"title","")), _c(getattr(e,"summary","")), _c(getattr(e,"author",""))])
            sc, ms = _score(skills, hay)
            url = _c(getattr(e,"link",""))
            if not url: continue
            co = _c(getattr(e,"author","Unknown"))
            em, li = _get_hr(co)
            out.append({"title":_c(getattr(e,"title","")) or "Untitled","company":co,"location":"Remote","url":url,"source":"Remotive","match_score":sc,"matched_skills":ms,"tags":[],"posted_at":_c(getattr(e,"published",_today())),"hr_email":em,"hr_linkedin":li})
        return out
    except Exception as e:
        logger.warning("Remotive failed: %s", e); return []

def fetch_all_jobs(skills, min_score=50):
    """Fetch from all sources. Only returns jobs with match_score >= min_score (default 50 = medium/high match)."""
    all_jobs = []
    for name, fn in [("RemoteOK",_remoteok),("Arbeitnow",_arbeitnow),("Jobicy",_jobicy),("The Muse",_themuse),("Remotive",_remotive)]:
        try:
            jobs = fn(skills)
            logger.info("%s → %d jobs", name, len(jobs))
            all_jobs.extend(jobs)
        except Exception as e:
            logger.warning("Error from %s: %s", name, e)
    seen, unique = set(), []
    for j in all_jobs:
        url = j.get("url","").strip()
        if url and url not in seen:
            seen.add(url); unique.append(j)
    if skills and min_score>0:
        unique = [j for j in unique if j["match_score"]>=min_score]
    unique.sort(key=lambda j: j["match_score"], reverse=True)
    logger.info("Total unique high-match jobs: %d", len(unique))
    return unique
