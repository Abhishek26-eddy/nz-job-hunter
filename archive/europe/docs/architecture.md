# Architecture

```mermaid
flowchart TB
    subgraph Scheduler
        A[Celery Beat<br/>Every 4 hours]
    end

    subgraph Crawlers
        B[Greenhouse Crawler]
        C[Lever Crawler]
        D[Ashby Crawler]
        E[Future: Workday, SmartRecruiters, LinkedIn, etc.]
    end

    subgraph Backend
        F[FastAPI REST API]
        G[SQLAlchemy + Alembic]
        H[AI Match Engine<br/>OpenAI]
        I[Resume / Cover Letter<br/>Generators]
        J[Visa Classifier]
        K[Notification Engine]
    end

    subgraph DataStores
        L[(PostgreSQL)]
        M[(Redis)]
        N[S3 Resumes & Cover Letters]
    end

    subgraph Frontend
        O[Next.js + Tailwind + shadcn/ui]
        P[Dashboard, Jobs, Companies, Analytics]
    end

    A --> B
    A --> C
    A --> D
    B --> F
    C --> F
    D --> F
    F --> G
    G --> L
    F --> M
    F --> N
    F --> H
    F --> I
    F --> J
    H --> F
    I --> F
    J --> F
    F --> K
    K --> Q[Slack / Telegram / Discord]
    O --> F
    P --> O
```

## Component Overview

### Crawler Layer
- Implements a plugin-style architecture with `BaseJobCrawler`.
- Each ATS (Greenhouse, Lever, Ashby) has its own parser.
- Jobs are filtered by target role keywords before storage.

### Deduplication Engine
- Every job posting is hashed with SHA-256.
- Existing jobs are updated rather than duplicated.
- `JobSnapshot` tracks title, description, location, and salary changes.

### AI Layer
- `JobMatcher` sends resume + JD to OpenAI and returns a structured score.
- `ResumeTailor` reorders existing bullets without lying.
- `CoverLetterGenerator` produces tailored 250-word cover letters.
- `VisaClassifier` uses regex heuristics for sponsorship signals.

### API Layer
- FastAPI with `/api/v1` versioning.
- OpenAPI docs auto-generated at `/docs`.
- Async SQLAlchemy sessions for non-blocking I/O.

### Frontend Layer
- Next.js App Router with Tanstack Query for data fetching.
- Sidebar navigation for Dashboard, Jobs, Companies, Analytics, Settings.

### Infrastructure Layer
- AWS ECS Fargate for API and Celery workers.
- RDS PostgreSQL for relational data.
- ElastiCache Redis for Celery broker and caching.
- S3 for resume/cover letter storage.
- CloudFront for frontend static hosting.
- Terraform for infrastructure as code.
