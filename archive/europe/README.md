# Europe Job Agent

AI-powered job discovery platform for **Senior DevOps / Platform / SRE / Cloud engineers** seeking visa-sponsored roles in Europe.

> **Architecture note:** This is designed as a **personal desktop tool**. You run it once or twice a day with a single command. Nothing runs in the background when you are not using it.

## Features

- **Company database** of 1,000+ European tech companies.
- **Job crawler** across Greenhouse, Lever, Ashby, and more.
- **Deduplication engine** with SHA-256 hashing and snapshot tracking.
- **AI match engine** (Google Gemini) scores jobs against your profile.
- **Resume & cover letter generators** tailored to each job.
- **Visa classifier** infers sponsorship likelihood from job descriptions.
- **Application tracker** with full pipeline: Saved → Applied → Interview → Offer.
- **Notifications** via Slack for high-match opportunities.
- **Modern dashboard** built with Next.js + Tailwind + shadcn/ui.

## Tech Stack

| Layer        | Technology                                   |
|--------------|-----------------------------------------------|
| Backend      | Python 3.12, FastAPI, SQLAlchemy, Alembic     |
| Database     | PostgreSQL, Redis                            |
| AI           | Google Gemini API                            |
| Frontend     | Next.js 14, TypeScript, Tailwind, shadcn/ui   |
| Local Infra  | Docker Compose                               |

## Quick Start

```bash
# 1. Clone and enter project
cd europe-job-agent

# 2. Copy environment files
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env

# 3. Edit backend/.env and set GEMINI_API_KEY (optional but recommended)

# 4. Run the daily workflow — starts Docker, migrates, seeds, crawls, matches, builds dashboard, opens browser
./daily-job-hunt.sh
```

The dashboard opens automatically at `http://localhost:3001`.  
Backend API docs are at `http://localhost:8002/docs`.

When finished, stop the stack:

```bash
docker-compose down
```

## Daily Workflow

The tool is intentionally **not** a 24/7 service. Run it manually when you want fresh jobs:

| Command | What it does |
|---------|--------------|
| `./daily-job-hunt.sh` | Full daily run and open browser |
| `./daily-job-hunt.sh --no-browser` | Full run without opening browser |
| `python3 run_daily.py --crawl-limit 200` | Run with custom crawl limit |

Steps executed:

1. Start Docker containers if not running.
2. Wait for backend health.
3. Run Alembic migrations.
4. Seed companies if database is empty.
5. Crawl supported ATS providers for new/updated jobs.
6. Run AI matching on unmatched jobs.
7. Rebuild frontend dashboard.
8. Open dashboard in browser.

## Manual Commands

Start the stack only:

```bash
docker-compose up -d
```

Run migrations:

```bash
docker-compose exec backend alembic upgrade head
```

Seed companies:

```bash
docker-compose exec backend python scripts/seed_companies.py
```

Trigger a crawl:

```bash
curl -X POST http://localhost:8002/api/v1/crawler/run?limit=50
```

Upload your master resume:

```bash
curl -X POST -F "file=@resume.pdf" -F "is_master=true" \
  http://localhost:8002/api/v1/resumes/upload
```

Match a job:

```bash
curl -X POST http://localhost:8002/api/v1/jobs/{job_id}/match
```

## Target Countries

United Kingdom, Ireland, Germany, Netherlands, Sweden, Denmark, Norway, Finland, Belgium, Luxembourg, Switzerland, Austria, France, Poland, Portugal, Spain.

## Project Structure

```
europe-job-agent/
├── backend/
│   ├── app/
│   │   ├── api/v1/endpoints/   # FastAPI routers
│   │   ├── ai/                 # OpenAI matchers, resume, cover letter
│   │   ├── core/               # Config, logging
│   │   ├── crawler/            # Greenhouse, Lever, Ashby crawlers
│   │   ├── db/                 # SQLAlchemy base + sessions
│   │   ├── models/             # Database models
│   │   ├── notifications/      # Slack, Telegram, etc.
│   │   ├── schemas/            # Pydantic schemas
│   │   ├── services/           # Business logic
│   │   └── tasks/              # Background task helpers
│   ├── alembic/                # Migrations
│   ├── scripts/                # Seed & verification scripts
│   └── tests/                  # Unit tests
├── frontend/
│   ├── app/                    # Next.js app router pages
│   ├── components/             # UI components
│   ├── e2e/                    # Playwright E2E tests
│   ├── lib/                    # API client
│   └── hooks/                  # Tanstack Query hooks
├── docker/                     # Dockerfiles
├── docs/                       # Architecture, API, ER, verification reports
├── run_daily.py                # Daily orchestration script
├── daily-job-hunt.sh           # Shell wrapper
└── scripts/load_test.py        # Backend load test
```

## Architecture & Docs

- `docs/architecture.md`
- `docs/er-diagram.md`
- `docs/api.md`
- `docs/verification-report.md`

## End-to-End Verification

A full verification run was completed. See `docs/verification-report.md` for:

- Docker health and resource usage
- Migration/schema verification
- Crawler, AI, frontend, and E2E test results
- Security scan results and mitigations
- Load test results
- Production readiness score

## Roadmap

- [x] Core models and database
- [x] Company seed (1,000+)
- [x] Greenhouse / Lever / Ashby crawlers
- [x] AI matching engine
- [x] Resume & cover letter generator
- [x] Visa classifier
- [x] FastAPI endpoints
- [x] Next.js dashboard (MVP)
- [x] Docker Compose setup
- [x] Playwright E2E tests
- [ ] LinkedIn public listing discovery
- [ ] One-click apply for supported ATS flows
- [ ] Recruiter finder & outreach messages
- [ ] Advanced analytics charts
- [ ] Mobile responsive polish
- [ ] Auth & multi-user support

## License

MIT
