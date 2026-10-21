import hashlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import text

from app.db.session import sync_engine, SessionLocal
from app.models.job import Job


def main():
    session = SessionLocal()
    try:
        company = session.execute(
            text("SELECT id, country_id FROM companies ORDER BY id LIMIT 1")
        ).first()
        if not company:
            print("No companies found")
            return

        description = "Senior DevOps Engineer. Kubernetes, Terraform, AWS, CI/CD. Visa sponsorship available."
        job = Job(
            external_id="test-123",
            platform="test",
            platform_url="https://example.com/job/123",
            title="Senior DevOps Engineer",
            description=description,
            description_hash=hashlib.sha256(description.encode()).hexdigest(),
            location="Berlin, Germany",
            workplace_type="hybrid",
            employment_type="full-time",
            application_url="https://boards.greenhouse.io/example/jobs/123",
            company_id=company.id,
            country_id=company.country_id,
            is_active=True,
            is_deleted=False,
            visa_sponsorship_inferred="Likely sponsorship",
        )
        session.add(job)
        session.commit()
        print(f"Created test job id={job.id}")
    finally:
        session.close()


if __name__ == "__main__":
    main()
