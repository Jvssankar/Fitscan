"""
AI Interview Engine — Anthropic API (claude-sonnet-4-6)
Half questions from JD, half from role-specific question bank.
Strict evaluation with detailed feedback per answer.
"""
import json, re, requests
from config import Config

QUESTION_BANK = {
    "python": ["Explain Python's GIL and its impact on multi-threading.","What are decorators in Python? Write a caching decorator.","Difference between deepcopy and shallow copy.","How does Python manage memory? Explain garbage collection."],
    "javascript": ["Explain event loop and call stack in JavaScript.","What is closure? Give a practical example.","Difference between == and === in JS.","Explain promises vs async/await."],
    "react": ["What is the virtual DOM and how does React use it?","Explain useState vs useReducer.","How do you prevent unnecessary re-renders?","What are React portals?"],
    "machine learning": ["Explain bias-variance tradeoff.","What is cross-validation and why use it?","Difference between L1 and L2 regularisation.","How does gradient descent work?"],
    "data science": ["How do you handle missing data?","Explain precision vs recall. When to prioritise which?","What is feature engineering?","How do you detect and handle outliers?"],
    "sql": ["What is the difference between INNER JOIN and LEFT JOIN?","Explain window functions with an example.","How do you optimise a slow SQL query?","What is database normalisation?"],
    "aws": ["Explain the difference between EC2, Lambda, and ECS.","What is an S3 bucket policy vs IAM policy?","How does auto-scaling work in AWS?","What is VPC and why use it?"],
    "docker": ["What is the difference between a Docker image and container?","Explain multi-stage Docker builds.","How does Docker networking work?","What is docker-compose used for?"],
    "system design": ["How would you design a URL shortener?","Explain CAP theorem.","How do you design a rate limiter?","What is eventual consistency?"],
    "general": ["Tell me about a challenging project you worked on and how you resolved it.","How do you handle disagreements with teammates?","Describe a time you had to learn something quickly under pressure.","What motivates you to do your best work?","Where do you see yourself in 3 years?","How do you prioritise tasks when everything seems urgent?"],
}

def _call_claude(system, user, max_tokens=1500):
    if not Config.ANTHROPIC_API_KEY:
        raise ValueError("ANTHROPIC_API_KEY not set.")
    r = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={"x-api-key":Config.ANTHROPIC_API_KEY,"anthropic-version":"2023-06-01","content-type":"application/json"},
        json={"model":Config.ANTHROPIC_MODEL,"max_tokens":max_tokens,"system":system,"messages":[{"role":"user","content":user}]},
        timeout=60
    )
    r.raise_for_status()
    data = r.json()
    tb = next((b for b in data.get("content",[]) if b.get("type")=="text"), None)
    if not tb: raise ValueError("No text in response.")
    return tb["text"]

def _parse_json(raw):
    t = re.sub(r'^```(?:json)?','',raw.strip(),flags=re.M)
    t = re.sub(r'```$','',t.strip(),flags=re.M).strip()
    s,e = t.find("{"), t.rfind("}")
    if s==-1 or e==-1:
        s,e = t.find("["), t.rfind("]")
    if s==-1 or e==-1: raise ValueError("No JSON found.")
    return json.loads(t[s:e+1])

def _bank_questions(skills, n=5):
    qs = []
    for skill in skills:
        for key, qlist in QUESTION_BANK.items():
            if key in skill.lower() or skill.lower() in key:
                qs.extend(qlist)
                break
    qs.extend(QUESTION_BANK["general"])
    seen, unique = set(), []
    for q in qs:
        if q not in seen:
            seen.add(q); unique.append(q)
    return unique[:n]

def generate_questions(job_title, job_description, resume_text, total=10):
    """Generate interview questions: ~half from JD via AI, ~half from question bank."""
    half = total // 2
    bank_qs = _bank_questions(_extract_role_skills(job_title, job_description), n=half)

    system = """You are a strict senior technical interviewer. Generate interview questions for a candidate.
Return ONLY a JSON array of question strings. No preamble, no markdown fences.
Questions must be:
- Technically rigorous and role-specific
- Mix of conceptual, coding-scenario, and behavioural
- Progressively harder
- Based on the job description requirements
Example: ["What is X?", "How would you implement Y?", "Describe a time when Z..."]"""

    user = f"""Job Title: {job_title}
Job Description (excerpt):
{job_description[:1500]}

Candidate Resume (excerpt):
{resume_text[:800] if resume_text else 'Not provided'}

Generate {half} interview questions targeting the specific skills and requirements in this JD.
Return ONLY the JSON array."""

    try:
        ai_qs_raw = _call_claude(system, user, max_tokens=800)
        ai_qs = _parse_json(ai_qs_raw)
        if not isinstance(ai_qs, list): ai_qs = []
        ai_qs = [str(q) for q in ai_qs[:half]]
    except Exception:
        ai_qs = []

    all_qs = ai_qs + bank_qs
    seen, final = set(), []
    for q in all_qs:
        if q not in seen:
            seen.add(q); final.append(q)
    return final[:total]

def evaluate_answer(question, answer, job_context=""):
    """Strictly evaluate one answer. Returns dict with score and feedback."""
    if not answer or len(answer.strip()) < 10:
        return {"score":0,"feedback":"No answer provided.","strengths":[],"weaknesses":["Answer was empty or too brief."],"model_answer":""}

    system = """You are a strict technical interviewer evaluating a candidate's answer.
Be rigorous — do not give high scores unless the answer is genuinely complete and accurate.
Return ONLY valid JSON with this exact schema:
{
  "score": <integer 0-10>,
  "feedback": "<2-3 sentence overall assessment>",
  "strengths": ["<up to 3 specific strengths of this answer>"],
  "weaknesses": ["<up to 3 specific gaps or errors>"],
  "model_answer": "<brief model answer or key points that should have been covered>"
}
Score guide: 0-3=Poor/wrong, 4-5=Partial, 6-7=Good, 8-9=Strong, 10=Exceptional"""

    user = f"""Question: {question}
Candidate's Answer: {answer}
Job Context: {job_context[:300] if job_context else 'General role'}
Evaluate strictly. Output JSON only."""

    try:
        raw = _call_claude(system, user, max_tokens=600)
        return _parse_json(raw)
    except Exception as e:
        return {"score":0,"feedback":f"Evaluation error: {e}","strengths":[],"weaknesses":["Could not evaluate."],"model_answer":""}

def generate_final_report(job_title, questions, answers, evaluations):
    """Generate a comprehensive interview performance report."""
    scores = [e.get("score",0) for e in evaluations if isinstance(e,dict)]
    avg = round(sum(scores)/max(len(scores),1), 1)
    overall = int(avg*10)

    all_weaknesses = []
    for e in evaluations:
        if isinstance(e,dict):
            all_weaknesses.extend(e.get("weaknesses",[]))

    system = """You are a senior hiring manager writing a post-interview performance report.
Be honest, specific, and constructive. Return ONLY valid JSON:
{
  "overall_grade": "A" | "B" | "C" | "D" | "F",
  "readiness": "Ready to Interview" | "Needs 2-4 Weeks Prep" | "Needs Significant Preparation",
  "executive_summary": "<3-4 sentence honest overall assessment>",
  "top_strengths": ["<up to 4 specific strengths observed>"],
  "critical_gaps": ["<up to 5 critical gaps that must be addressed>"],
  "study_plan": ["<up to 5 specific topics to study before the real interview>"],
  "interview_tips": ["<up to 4 tips on delivery, communication, and technique>"]
}"""

    user = f"""Job Title: {job_title}
Average score: {avg}/10 ({overall}%)
Individual scores: {scores}
Common weaknesses observed: {list(set(all_weaknesses))[:10]}
Generate the performance report. JSON only."""

    try:
        raw = _call_claude(system, user, max_tokens=1000)
        report = _parse_json(raw)
        report["overall_score"] = overall
        report["avg_per_question"] = avg
        return report
    except Exception:
        grade = "A" if avg>=9 else "B" if avg>=7 else "C" if avg>=5 else "D" if avg>=3 else "F"
        return {"overall_grade":grade,"readiness":"Needs review","executive_summary":f"Scored {avg}/10 on average across {len(scores)} questions.","top_strengths":[],"critical_gaps":list(set(all_weaknesses))[:5],"study_plan":[],"interview_tips":[],"overall_score":overall,"avg_per_question":avg}

def _extract_role_skills(title, jd):
    from services.analyzer import extract_skills
    return extract_skills(f"{title} {jd}")
