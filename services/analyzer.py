import re

SKILL_DICT = [
    "python","java","javascript","typescript","c++","c#","go","golang","rust","kotlin",
    "swift","ruby","php","scala","r","matlab","bash","shell","powershell","dart",
    "html","css","react","reactjs","angular","vue","vuejs","nextjs","svelte","jquery",
    "bootstrap","tailwind","sass","webpack","redux","graphql","rest","restful","json",
    "nodejs","node.js","express","django","flask","fastapi","spring","springboot",
    "laravel","rails","asp.net",".net","dotnet",
    "android","ios","react native","flutter","xamarin",
    "sql","mysql","postgresql","postgres","mongodb","sqlite","redis","cassandra","oracle",
    "dynamodb","firebase","elasticsearch","snowflake","bigquery","hive","mariadb",
    "aws","azure","gcp","google cloud","docker","kubernetes","k8s","terraform",
    "ansible","jenkins","ci/cd","github actions","gitlab ci","linux","unix","nginx",
    "apache","heroku","render","vercel","netlify","prometheus","grafana","datadog",
    "machine learning","deep learning","neural network","nlp","computer vision",
    "tensorflow","pytorch","keras","scikit-learn","sklearn","pandas","numpy",
    "matplotlib","seaborn","opencv","hugging face","transformers","llm","generative ai",
    "rag","langchain","data science","data analysis","statistics","regression",
    "classification","clustering","random forest","xgboost","lightgbm","mlflow","airflow",
    "etl","spark","hadoop","kafka","dbt","power bi","tableau","looker","excel",
    "cybersecurity","penetration testing","ethical hacking","firewall","ssl","oauth","jwt",
    "git","github","gitlab","bitbucket","jira","confluence","agile","scrum","kanban",
    "tdd","unit testing","selenium","jest","pytest","junit","postman","swagger","figma",
    "communication","leadership","teamwork","problem solving","project management",
]

SECTION_KEYS = {
    "contact":    ["email","phone","mobile","linkedin","github","address","contact"],
    "summary":    ["summary","objective","profile","about","introduction","overview"],
    "experience": ["experience","employment","work history","career","professional","internship","intern"],
    "education":  ["education","degree","university","college","bachelor","master","phd","b.tech","m.tech","b.e","b.sc"],
    "skills":     ["skills","technologies","tech stack","tools","competencies","proficiencies"],
    "projects":   ["project","projects","portfolio","built","developed","created"],
    "certifications": ["certification","certificate","certified","credential","course","training"],
}

WEAK = ["responsible for","worked on","helped with","assisted in","involved in",
        "participated in","duties included","familiar with","exposure to","basic knowledge"]
VERBS = ["developed","built","designed","implemented","created","led","managed",
         "optimized","improved","reduced","increased","automated","deployed","launched",
         "delivered","architected","engineered","established","streamlined","mentored",
         "collaborated","integrated","migrated","scaled","analysed","analyzed","researched"]
METRIC_RE = re.compile(
    r'\b(\d+[\.,]?\d*\s*(%|percent|x|times|hours?|days?|weeks?|months?|years?|'
    r'users?|clients?|k|m|million|billion|requests?|ms|seconds?))\b', re.I)
RISKY_RE = re.compile(r'[|]{2,}|\t{3,}|_{10,}')

def _lo(t): return t.lower()
def _skills(t):
    lo = _lo(t)
    return [s for s in SKILL_DICT if re.search(r'\b'+re.escape(s)+r'\b', lo)]
def _sections(t):
    lo = _lo(t)
    return {sec: any(re.search(r'\b'+re.escape(k)+r'\b', lo) for k in kws)
            for sec, kws in SECTION_KEYS.items()}
def _clamp(v): return int(max(0, min(100, round(v))))

def run_general_scan(resume_text):
    t = resume_text.strip()
    wc = len(t.split())
    secs = _sections(t); sf = sum(secs.values()); st = len(secs)
    skills = _skills(t)
    metrics = len(METRIC_RE.findall(t))
    av = sum(1 for v in VERBS if re.search(r'\b'+v+r'\b', _lo(t)))
    wp = sum(1 for p in WEAK if p in _lo(t))
    risky = bool(RISKY_RE.search(t))
    has_email = bool(re.search(r'[\w.\-]+@[\w.\-]+\.\w{2,}', t))
    has_phone = bool(re.search(r'(\+?\d[\d\s\-().]{7,}\d)', t))

    struct = _clamp((sf/st)*15 + (5 if has_email and has_phone else 2 if has_email else 0)
                    + (5 if 300<=wc<=800 else 3 if wc<300 else 2) + (-8 if risky else 0)) * 100 // 25
    struct = _clamp(struct)
    content = _clamp((min(10,metrics*2)+min(10,av*1.2)-min(8,wp*2)+5) / 25 * 100)
    keyword = _clamp(min(25, len(skills)*2) / 25 * 100)
    readability = 100 if 400<=wc<=700 else 80 if 300<=wc<400 or 700<wc<=900 else 60 if 200<=wc<300 or 900<wc<=1200 else 35

    ats = _clamp(struct*.25 + content*.25 + keyword*.25 + readability*.25)
    verdict = "ATS-Ready" if ats>=75 else "Minor Improvements Needed" if ats>=50 else "High Risk of ATS Rejection"

    strengths = []
    if sf>=5: strengths.append(f"All key sections present ({sf}/{st})")
    if len(skills)>=8: strengths.append(f"Strong skill coverage ({len(skills)} skills detected)")
    if metrics>=3: strengths.append(f"Good quantified achievements ({metrics} metrics)")
    if av>=5: strengths.append(f"Strong action verbs ({av} detected)")
    if has_email and has_phone: strengths.append("Complete contact information")
    if not risky: strengths.append("Clean ATS-friendly formatting")

    issues = []
    ms = [s for s,v in secs.items() if not v]
    if ms: issues.append({"title":"Missing Key Sections","detail":f"Missing: {', '.join(ms)}.","fix":f"Add headings for: {', '.join(ms[:3])}."})
    if metrics<2: issues.append({"title":"No Quantifiable Achievements","detail":"No measurable results found.","fix":"Add numbers: 'Reduced load time by 40%', 'Served 10k users'."})
    if wp>=2: issues.append({"title":"Weak/Passive Language","detail":f"Found {wp} passive phrases.","fix":"Replace with action verbs: Developed, Built, Led, Reduced."})
    if len(skills)<5: issues.append({"title":"Low Keyword Density","detail":f"Only {len(skills)} skills detected.","fix":"Add a Skills section listing all your tools and technologies explicitly."})
    if risky: issues.append({"title":"ATS-Risky Formatting","detail":"Tables or columns detected — may break ATS.","fix":"Use single-column plain text. Avoid tables and text boxes."})
    if not has_email: issues.append({"title":"No Email Detected","detail":"Email not found in extracted text.","fix":"Put email in plain text at top, not inside images or headers."})
    if wc<200: issues.append({"title":"Resume Too Short","detail":f"Only {wc} words.","fix":"Expand with 2–3 bullet points per role. Aim for 400–700 words."})
    elif wc>1000: issues.append({"title":"Resume Too Long","detail":f"{wc} words — may exceed 2 pages.","fix":"Trim older experience. Focus on last 3–5 years."})

    return {"verdict":verdict,"atsScore":ats,"breakdown":{"structureFormatting":struct,"contentQuality":content,"keywordOptimization":keyword,"readabilityLength":readability},"summary":_gsummary(ats,sf,st,len(skills),metrics,wp,wc),"strengths":strengths[:4],"issues":issues[:6],"_skills":skills}

def _gsummary(sc,sf,st,sk,m,wp,wc):
    if sc>=80: return f"Strong ATS-ready resume — {sf}/{st} sections, {sk} skills, {m} metrics."
    if sc>=65: return f"Good foundation ({sf}/{st} sections, {sk} skills) — minor improvements needed."
    if sc>=45: return f"Several ATS issues detected — sections, keywords, or phrasing need work."
    return "High risk of ATS rejection — critical sections missing or formatting issues found."

def run_match_scan(resume_text, jd_text):
    STOP = {"and","the","to","of","in","a","an","for","with","or","is","are","be","on","at","by","as","this","that","we","you","our","your","will","have","has","from","their","they","all","also","more","can","not","but","if","it","its","who","was","been","were"}
    rw = set(re.findall(r'\b\w[\w\+\#\.]*\b', resume_text.lower()))
    jw = set(re.findall(r'\b\w[\w\+\#\.]*\b', jd_text.lower()))
    rs = set(_skills(resume_text)); js = set(_skills(jd_text))
    matched = list(rs&js); missing = list(js-rs)
    jkw = {w for w in jw if len(w)>2 and w not in STOP}
    km = _clamp(len(rw&jkw)/max(len(jkw),1)*100)
    sm = _clamp(len(matched)/max(len(js),1)*100) if js else 50
    exp_req = _yrreq(jd_text); exp_res = _yrres(resume_text)
    em = 100 if exp_req==0 else (100 if exp_res>=exp_req else 70 if exp_res>=exp_req*.7 else 40)
    secs = _sections(resume_text)
    fm = _clamp(sum(secs.values())/len(secs)*100)
    ats = _clamp(km*.30+sm*.35+em*.20+fm*.15)
    verdict = "Strong Match" if ats>=70 else "Moderate Match" if ats>=45 else "Weak Match"
    suggs = []
    if missing: suggs.append(f"Add these missing skills if you have them: {', '.join(missing[:4])}.")
    top_kw = list(jkw-rw)[:4]
    if top_kw: suggs.append(f"Weave these JD keywords naturally into your bullets: {', '.join(top_kw)}.")
    if exp_req>0 and exp_res<exp_req: suggs.append(f"JD asks {exp_req}+ years — highlight internships and projects to bridge gap.")
    suggs.append("Mirror the exact job title from the JD in your summary section.")
    suggs.append("Add a 2–3 line tailored professional summary mentioning the role and your top 3 matching skills.")
    alts = _altroles(rs) if ats<60 else []
    return {"verdict":verdict,"atsScore":ats,"breakdown":{"keywordMatch":km,"skillsMatch":sm,"experienceMatch":em,"formatCompliance":fm},"summary":_msummary(ats,matched,missing,verdict),"matchedSkills":matched[:8],"missingSkills":missing[:8],"suggestions":suggs[:5],"alternativeRoles":alts[:3],"_skills":list(rs)}

def _yrreq(t):
    m = re.findall(r'(\d+)\+?\s*(?:to\s*\d+\s*)?years?', t, re.I)
    return int(m[0]) if m else 0

def _yrres(t):
    yrs = sorted([int(y) for y in re.findall(r'\b(20\d{2})\b', t)])
    return max(0, yrs[-1]-yrs[0]) if len(yrs)>=2 else 0

def _msummary(sc,m,ms,v):
    if sc>=70: return f"Strong match — {len(m)} skills align. Tailor your summary to mirror the JD language."
    if sc>=45: return f"Moderate match — {len(m)} skills matched, {len(ms)} gaps. Adding keywords could push to Strong Match."
    return f"Weak match — only {len(m)} skills overlap. Consider targeting a better-fitting role or building missing skills."

def _altroles(skills):
    roles = [
        ({"python","machine learning","pandas","scikit-learn","tensorflow","pytorch"},"Data Scientist / ML Engineer","Your Python and ML skills are a strong foundation for data science roles."),
        ({"python","flask","django","fastapi","sql","postgresql"},"Backend Python Developer","Your backend stack fits many Python engineering openings."),
        ({"react","javascript","html","css","typescript","nextjs"},"Frontend / React Developer","Your frontend skills match a large number of web roles."),
        ({"docker","kubernetes","aws","azure","gcp","terraform","linux"},"DevOps / Cloud Engineer","Your infra skills are in high demand for DevOps/cloud."),
        ({"sql","tableau","power bi","excel","data analysis"},"Data Analyst","Your analytics skills suit data analyst positions."),
        ({"java","spring","springboot","sql"},"Java Backend Developer","Your Java + Spring stack suits enterprise roles."),
        ({"android","kotlin","ios","swift","react native","flutter"},"Mobile Developer","Your mobile skills suit Android/iOS and cross-platform roles."),
    ]
    scored = [(len(skills&r),t,d) for r,t,d in roles if len(skills&r)>0]
    scored.sort(reverse=True)
    return [{"role":t,"reason":d} for _,t,d in scored]

def extract_skills(text):
    return _skills(text)

def tailor_resume(resume_text, jd_text):
    """Rule-based resume tailoring — adds missing keywords and improves phrasing."""
    rs = set(_skills(resume_text)); js = set(_skills(jd_text))
    missing = list(js - rs)
    STOP = {"and","the","to","of","in","a","an","for","with","or","is","are","be","on"}
    jkw = set(re.findall(r'\b\w[\w\+\#\.]*\b', jd_text.lower())) - STOP
    missing_kw = list(jkw - set(re.findall(r'\b\w[\w\+\#\.]*\b', resume_text.lower())))

    suggestions = []
    if missing:
        suggestions.append(f"ADD THESE SKILLS to your Skills section (from the JD):\n  → {', '.join(missing[:10])}")
    if missing_kw:
        top = [k for k in missing_kw if len(k)>3][:8]
        if top:
            suggestions.append(f"WEAVE THESE KEYWORDS into your bullets/summary:\n  → {', '.join(top)}")

    jd_title = ""
    for line in jd_text.split("\n")[:5]:
        line = line.strip()
        if line and len(line) < 80:
            jd_title = line; break

    tailored = resume_text
    lo = resume_text.lower()
    if "summary" not in lo and "objective" not in lo and "profile" not in lo:
        if missing[:3]:
            summary_insert = (
                f"\n\nPROFESSIONAL SUMMARY\n"
                f"Results-driven professional with expertise in {', '.join(list(rs)[:4])}. "
                f"Seeking to leverage skills in {jd_title or 'this role'} with a focus on "
                f"{', '.join(missing[:2]) if missing else 'delivering impact'}.\n"
            )
            tailored = summary_insert + tailored

    for wp in WEAK:
        idx = tailored.lower().find(wp)
        while idx != -1:
            tailored = tailored[:idx] + f"[REPLACE '{wp}' WITH AN ACTION VERB]" + tailored[idx+len(wp):]
            idx = tailored.lower().find(wp, idx+1)

    report = {
        "original_score": run_match_scan(resume_text, jd_text)["atsScore"],
        "tailored_score": run_match_scan(tailored, jd_text)["atsScore"],
        "missing_skills": missing[:10],
        "missing_keywords": [k for k in missing_kw if len(k)>3][:8],
        "suggestions": suggestions,
        "tailored_text": tailored,
    }
    return report
