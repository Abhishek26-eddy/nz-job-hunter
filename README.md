# NZ Visa Job Hunter

Finds New Zealand DevOps / SRE / Platform / Cloud / Forward Deployed / AI-infra
jobs that can carry the [India Skilled Work Visa](https://www.immigration.govt.nz/visas/india-skilled-work-visa/),
and emails you **only** the ones where the employer can sponsor.

The visa needs a full-time (30h+) offer from an **AEWV-accredited employer**, for a
role the employer describes as Software Engineer, Software and Applications
Programmer or ICT Project Manager. Places are capped (1,000 for ICT) and first
come, first served, so speed matters.

## What it does every 15 minutes

1. Searches **Seek NZ** (15 keyword searches) and **LinkedIn** (5 boolean searches, public pages, no login).
2. Keeps jobs whose title fits your domain (`hunter/config.py`: `CORE_TITLE`, `EXCLUDE_TITLE`).
3. Reads the full ad and flags:
   - ⛔ **hard blockers**: "no visa sponsorship", "citizens/residents only", security clearance
   - ⚠️ **soft blockers**: "must already have the right to work", "must be based in NZ"
   - 👍 **positives**: "visa sponsorship available", relocation support
4. Looks the employer up in the **INZ accredited employer list** (cached for 7 days).
   Recruitment agencies are flagged: their own accreditation says nothing about the client.
5. Scores each job against your skills (`SKILLS` in the config).
6. **Emails only visa-ready jobs**: accredited employer (or the ad offers sponsorship), no blockers,
   not part time. Everything else waits on the dashboard.
7. Watches the visa page and emails you if what it says about **places available** changes.

## Layout

| Path | What |
|---|---|
| `hunter/` | The hunter (Python 3.12, standard library only) |
| `hunter/config.py` | Search terms, title rules, blockers, skills, agencies, aliases |
| `data/jobs.json` | Every tracked job, committed by the workflow |
| `data/accreditation.json` | INZ lookup cache |
| `site/index.html` | Dashboard (static; reads `jobs.json` + `meta.json`) |
| `.github/workflows/hunt.yml` | The 15-minute schedule |
| `vercel.json` | Dashboard hosting; only redeploys when `jobs.json` changes |
| `archive/europe/` | The old Europe job agent, untouched |

## Run it locally

```bash
python3 -m hunter.run --no-email
python3 -m http.server 8000
```

Then open http://localhost:8000/site/. Run the tests with
`python3 -m unittest discover -s tests`.

## Set up (once)

1. **GitHub repo.** Push this folder to a **public** repo: public repos get unlimited
   Actions minutes, while a private one would burn the free 2,000 min/month in about 5 days.
   Only public job ads and code are committed (`.env` files are git-ignored).
2. **Email.** Create a Gmail [app password](https://myaccount.google.com/apppasswords), then in
   the repo go to Settings → Secrets and variables → Actions and add:
   - secrets `SMTP_USER` (your Gmail address), `SMTP_PASSWORD` (the app password), `ALERT_TO` (where alerts go)
   - variable `SITE_URL` (the Vercel URL, once you have it)
3. **Vercel.** Import the repo in Vercel and leave the build settings to `vercel.json`.
4. Run the workflow once by hand (Actions → Hunt NZ jobs → Run workflow).

## Tuning

- Missing a kind of job? Add a search to `SEEK_KEYWORDS` / `LINKEDIN_QUERIES` and a title pattern to `CORE_TITLE`.
- Employer shows "not on public list" but you know it is accredited? Add the ad name to `EMPLOYER_ALIASES`.
- An agency not detected? Add it to `RECRUITERS`.
