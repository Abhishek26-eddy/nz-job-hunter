# API Reference

Base URL: `/api/v1`

## Authentication

For the MVP, a default user is created on first upload. Authentication will be added in a later iteration.

## Companies

### List companies
`GET /api/v1/companies`

Query params:
- `skip` (int)
- `limit` (int)
- `country_code` (string, optional)
- `industry` (string, optional)
- `visa_sponsorship` (string, optional)
- `is_active` (bool, optional)

### Get company
`GET /api/v1/companies/{id}`

### Update company
`PATCH /api/v1/companies/{id}`

Body: `{ "visa_sponsorship": "Likely", "is_active": true }`

## Jobs

### List jobs
`GET /api/v1/jobs`

Query params:
- `skip`, `limit`
- `country_code`
- `company_id`
- `search` (text search on title/description)
- `visa_sponsorship`
- `min_match_score` (float, 0–100)
- `remote_only` (bool)
- `should_apply` (bool)

### Get job
`GET /api/v1/jobs/{id}`

### AI match job
`POST /api/v1/jobs/{id}/match`

Returns:
```json
{
  "job_id": 1,
  "match_score": 87.5,
  "strengths": ["Kubernetes", "Terraform"],
  "missing_skills": ["Azure", "Go"],
  "visa_sponsorship_inferred": "Likely sponsorship",
  "should_apply": true,
  "reason": "Strong DevOps fit..."
}
```

## Applications

### List applications
`GET /api/v1/applications`

### Create application
`POST /api/v1/applications`

Body:
```json
{
  "job_id": 1,
  "status": "saved"
}
```

### Get application
`GET /api/v1/applications/{id}`

### Update status
`PATCH /api/v1/applications/{id}`

Body: `{ "status": "applied", "notes": "Applied via Greenhouse" }`

## Resumes

### List resumes
`GET /api/v1/resumes`

### Upload resume (PDF)
`POST /api/v1/resumes/upload`

Form data:
- `file` (PDF)
- `is_master` (bool)

### Tailor resume for job
`POST /api/v1/resumes/{resume_id}/tailor/{job_id}`

Returns tailored `ResumeRead`.

## Cover Letters

### Generate cover letter
`POST /api/v1/cover-letters/generate/{job_id}?resume_id=1`

## AI

### Match job
`POST /api/v1/ai/match/{job_id}`

Requires a master resume to be uploaded first.

### Tailor resume
`POST /api/v1/ai/tailor-resume/{job_id}?resume_id=1`

### Generate cover letter
`POST /api/v1/ai/cover-letter/{job_id}?resume_id=1`

## One-Click Apply

### Get safe apply action
`POST /api/v1/apply/jobs/{job_id}`

Returns either an `auto-open` action for known safe ATS URLs or a `manual` intent.

## Crawler

### Trigger crawl
`POST /api/v1/crawler/run`

Query param: `limit` (number of companies to crawl)

Response: `{ "crawled": 50, "new_jobs": 12, "updated_jobs": 3 }`

## Analytics

### Summary
`GET /api/v1/analytics/summary`

Response:
```json
{
  "total_jobs": 120,
  "total_companies": 1200,
  "total_applications": 5,
  "status_counts": { "saved": 2, "applied": 3 },
  "top_countries": [
    {"country": "Germany", "jobs": 45}
  ]
}
```
