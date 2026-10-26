# FIT/SCAN — AI Career Accelerator

A full-stack Python (Flask) career platform with **zero mandatory API key** (only the AI Interview tab needs one).

---

## Features

| Tab | What it does |
|---|---|
| **Upload Resume** | PDF / DOCX / TXT extraction — skills auto-detected, jobs searched instantly |
| **ATS Scanner** | Rule-based ATS health check OR job-fit match scan — instant, no API |
| **Tailor Resume** | Keyword gap analysis + tailored resume preview with score improvement |
| **Job Matches** | Real jobs from 5 boards (50%+ match only) with HR email + LinkedIn contact |
| **Application Tracker** | Track status (Applied → Interview → Offer), follow-up dates, HR contacts |
| **AI Interview** | Strict AI interviewer — half JD questions + half question bank, per-answer scoring, final report |
| **History** | All scans saved per user account — full report replay |

---

## Project structure

```
fitscan/
├── app.py                   Flask app + all routes
├── config.py                Config (reads .env / env vars)
├── extensions.py            SQLAlchemy + Flask-Login
├── models.py                User, Resume, ScanHistory, JobMatch,
│                            ApplicationTracker, InterviewSession
├── wsgi.py                  Gunicorn entry point
├── render.yaml              Render deploy (web + cron + Postgres)
├── requirements.txt
├── .env.example             Copy to .env before running locally
├── .gitignore
├── templates/
│   ├── index.html           Main app (7-tab SPA)
│   └── auth.html            Sign In / Sign Up page
└── services/
    ├── extractor.py         PDF / DOCX / TXT text extraction
    ├── analyzer.py          Rule-based ATS engine + resume tailor
    ├── job_fetcher.py       5 real job board APIs + HR contacts
    ├── interview.py         AI Interview engine (Anthropic API)
    └── refresh.py           Daily job refresh logic
```

---

## Running locally on Windows (VS Code)

### Step 1 — Open project in VS Code

Unzip `fitscan.zip`, open VS Code → **File → Open Folder** → select the `fitscan` folder.

Open integrated terminal: **Ctrl + `**

### Step 2 — Create virtual environment

```powershell
python -m venv venv
```

### Step 3 — Activate virtual environment

```powershell
venv\Scripts\Activate.ps1
```

If you get a permissions error, run this once first:

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

Then activate again. You'll see `(venv)` at the start of your prompt.

### Step 4 — Install dependencies

```powershell
pip install -r requirements.txt
```

### Step 5 — Set up .env file

```powershell
copy .env.example .env
```

Open `.env` in VS Code and fill in your `ANTHROPIC_API_KEY` (only needed for AI Interview).
Everything else works with the default values.

### Step 6 — Run the app

```powershell
python app.py
```

Open your browser: **http://localhost:5000**

- You'll be redirected to the Sign In page
- Click "Create Account" to register
- The SQLite database (`fitscan.db`) is created automatically

---

## How the AI Interview works

1. You paste a job title + job description
2. Claude generates ~5 questions targeting the JD's specific requirements
3. ~5 questions come from a curated technical question bank (role-matched)
4. You answer all 10 questions in the browser
5. Claude evaluates each answer: score (0–10), feedback, strengths, gaps, model answer
6. A final report is generated: Grade (A–F), readiness verdict, study plan, interview tips
7. Report is saved to your Interview History permanently

---

## How daily job refresh works

- Render cron calls `POST /api/refresh` every day at 06:00 UTC
- Fetches fresh listings from RemoteOK, Arbeitnow, Jobicy, The Muse, Remotive
- Only jobs with **50%+ skill match** are saved (high-quality matches only)
- Each job card shows the company's HR email + LinkedIn jobs page for direct follow-up
- You can also trigger a manual refresh any time from the Job Matches tab

---

## Resume/Interview talking points

| Feature | Skill demonstrated |
|---|---|
| Auth (signup/login) | Flask-Login, password hashing, session management |
| PDF/DOCX extraction | pdfplumber, python-docx, binary file handling |
| Rule-based ATS engine | NLP without APIs: regex, scoring algorithms, keyword matching |
| Resume tailoring | Gap analysis, keyword injection, passive phrase detection |
| 5 job board APIs | HTTP aggregation, deduplication, scoring, error handling |
| Daily cron refresh | Scheduled jobs, server automation, Render cron |
| AI Interview | Anthropic API, prompt engineering, structured evaluation |
| Application tracker | Full CRUD, status management, follow-up dates |
| SQLAlchemy + Postgres | ORM, relational models, migrations |
| Render deployment | Cloud hosting, IaC (render.yaml), environment management |
| Vanilla JS SPA | REST API consumption, 7-tab dynamic UI, no framework |
