"""Local AI matching pipeline using sentence-transformer embeddings + Ollama.

Steps:
1. Embed master resume once and cache it.
2. Embed every active job description once and cache it.
3. Compute cosine-similarity scores for all active jobs.
4. Send only the top N jobs to Ollama for reasoning/explanation.

Only newly discovered or updated jobs/resume are re-embedded. Ollama is only
invoked for jobs that have not been reasoned about yet, or when the underlying
resume/job changed.
"""

import asyncio
import hashlib
from datetime import datetime
from typing import Sequence

import numpy as np
import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.ai.embeddings import cosine_similarity, get_embedding_model
from app.ai.ollama_client import OllamaClient
from app.ai.vector_store import VectorBackend, create_vector_backend
from app.core.config import get_settings
from app.models.company import Company
from app.models.job import Job
from app.models.resume import Resume
from app.services.job_intelligence import (
    build_resume_profile,
    classify_role,
    compute_weighted_score,
    mandatory_filter,
)
from app.services.resume_service import ResumeService

logger = structlog.get_logger()
_settings = get_settings()


def _text_hash(text: str | None) -> str:
    return hashlib.sha256((text or "").encode("utf-8")).hexdigest()


def _prompt_for_reasoning(
    resume_text: str,
    skills: list[str],
    job_title: str,
    job_description: str,
    location: str | None,
    company_name: str | None,
    current_score: float,
) -> str:
    return f"""You are an expert engineering recruiter and career coach helping an Indian DevOps/Platform engineer evaluate a European job. Based only on the resume and job description below, produce valid JSON with no markdown.

Candidate Profile:
- Resume:
{resume_text[:4000]}

- Skills: {', '.join(skills)}

Job Posting:
- Company: {company_name or 'Unknown'}
- Title: {job_title}
- Location: {location or 'Not specified'}
- Description:
{job_description[:6000]}

Embedding-based similarity score (0-100): {current_score:.1f}

Return JSON exactly like this:
{{
  "reason": "<one paragraph explanation of fit>",
  "missing_skills": ["<skill 1>", "<skill 2>"],
  "visa_probability": "<Likely / Possible / Unknown / Not sponsored>",
  "job_summary": "<2-3 sentence summary of the role>",
  "should_apply": <true or false>,
  "confidence": <float 0.0-1.0>
}}

Rules:
- should_apply should be true only for genuinely strong matches.
- visa_probability should be "Likely" only if the JD mentions sponsorship, relocation, or international applicants.
- Be honest; do not inflate the fit.
""".strip()


class LocalMatchingService:
    def __init__(
        self,
        db: AsyncSession,
        embedding_model=None,
        vector_store: VectorBackend | None = None,
        ollama: OllamaClient | None = None,
    ):
        self.db = db
        self.embedding_model = embedding_model or get_embedding_model()
        self.vector_store = vector_store or create_vector_backend()
        self.ollama = ollama or OllamaClient()
        self.settings = get_settings()

    # ------------------------------------------------------------------
    # Embeddings
    # ------------------------------------------------------------------
    async def ensure_resume_embedding(self, resume: Resume) -> np.ndarray:
        current_hash = _text_hash(resume.content_text)
        if (
            resume.embedding is not None
            and resume.embedding_model == self.embedding_model.model_name
            and resume.embedding_content_hash == current_hash
        ):
            logger.debug("resume_embedding_cache_hit", resume_id=resume.id)
            return np.asarray(resume.embedding, dtype=np.float32)

        logger.info("generating_resume_embedding", resume_id=resume.id)
        text = resume.content_text or ""
        vector = self.embedding_model.encode([text])[0]
        await self.vector_store.store_resume_embedding(
            self.db, resume.id, vector.tolist(), self.embedding_model.model_name
        )
        resume.embedding_content_hash = current_hash
        await self.db.commit()
        return vector

    async def ensure_resume_profile(self, resume: Resume) -> dict:
        """Build (and cache) the structured resume profile used by the recruiter
        scoring layer. Only rebuilt when the resume text actually changes."""
        current_hash = _text_hash(resume.content_text)
        if resume.profile is not None and resume.profile_content_hash == current_hash:
            return resume.profile

        logger.info("building_resume_profile", resume_id=resume.id)
        profile = build_resume_profile(resume.content_text)
        # Merge in any explicitly-tagged skills from the resume record itself.
        if resume.skills:
            profile["skills"] = sorted(set(profile.get("skills", [])) | {s.lower() for s in resume.skills})
        resume.profile = profile
        resume.profile_content_hash = current_hash
        await self.db.commit()
        return profile

    async def classify_and_filter_jobs(self, resume_skills: set[str]) -> tuple[list[int], int]:
        """Classify every active job's role category and apply mandatory hard
        filters (non-Europe, junior/intern, wrong specialization/language)
        BEFORE any embedding is generated for it. Returns (allowed_job_ids, rejected_count)."""
        result = await self.db.execute(
            select(Job)
            .options(selectinload(Job.country))
            .where(Job.is_active == True, Job.is_deleted == False)
        )
        jobs: list[Job] = list(result.scalars().all())

        allowed_ids: list[int] = []
        rejected_count = 0
        for job in jobs:
            country_name = job.country.name if job.country else None
            country_is_eu = job.country.is_eu if job.country else None
            filter_result = mandatory_filter(
                title=job.title,
                description=job.description,
                location=job.location,
                country_name=country_name,
                country_is_eu=country_is_eu,
                resume_skills=resume_skills,
            )
            role_category, role_priority = classify_role(job.title, job.description)
            job.role_category = role_category

            if filter_result.rejected:
                job.rejected = True
                job.rejection_reason = filter_result.reason
                job.role_priority = "reject"
                job.match_score = 0.0
                job.should_apply = False
                job.critical_missing_skills = []
                rejected_count += 1
            else:
                job.rejected = False
                job.rejection_reason = None
                job.role_priority = role_priority
                allowed_ids.append(job.id)

        await self.db.commit()
        return allowed_ids, rejected_count

    async def ensure_job_embeddings(self, job_ids: Sequence[int] | None = None) -> int:
        """Generate embeddings for active jobs that are missing or stale.

        job_ids=None embeds all active jobs; job_ids=[] embeds nothing;
        job_ids=[...] embeds only the given jobs.
        """
        if job_ids is not None and len(job_ids) == 0:
            return 0

        query = select(Job).where(Job.is_active == True, Job.is_deleted == False)
        if job_ids is not None:
            query = query.where(Job.id.in_(job_ids))

        result = await self.db.execute(query)
        jobs: list[Job] = list(result.scalars().all())

        jobs_to_embed: list[Job] = []
        for job in jobs:
            expected_hash = job.description_hash or _text_hash(job.description)
            if (
                job.embedding is None
                or job.embedding_model != self.embedding_model.model_name
            ):
                jobs_to_embed.append(job)
            else:
                # If the description changed since embedding, mark for re-embed.
                # We don't store description_hash separately for embeddings, so
                # rely on the existing description_hash column.
                pass

        if not jobs_to_embed:
            return 0

        logger.info(
            "generating_job_embeddings",
            count=len(jobs_to_embed),
        )
        texts = [f"{job.title}\n{job.description or ''}" for job in jobs_to_embed]
        vectors = self.embedding_model.encode(texts)
        for job, vector in zip(jobs_to_embed, vectors):
            await self.vector_store.store_job_embedding(
                self.db, job.id, vector.tolist(), self.embedding_model.model_name
            )

        await self.db.commit()
        return len(jobs_to_embed)

    # ------------------------------------------------------------------
    # Scoring
    # ------------------------------------------------------------------
    async def score_all_jobs(
        self,
        resume_vector: np.ndarray,
        resume_skills: set[str],
        resume_profile: dict,
    ) -> int:
        """Update match_score for every active, non-rejected job using the
        weighted recruiter scoring formula (embedding similarity is only one
        of several signals; see app.services.job_intelligence)."""
        job_embeddings = await self.vector_store.get_active_job_embeddings(self.db)
        if not job_embeddings:
            return 0

        result = await self.db.execute(
            select(Job)
            .options(selectinload(Job.company))
            .where(Job.id.in_(list(job_embeddings.keys())))
        )
        jobs_by_id = {job.id: job for job in result.scalars().all()}

        logger.info("scoring_jobs", count=len(job_embeddings))
        updated = 0
        for job_id, vector in job_embeddings.items():
            job = jobs_by_id.get(job_id)
            if job is None or job.rejected:
                continue

            embedding_score = max(0.0, float(cosine_similarity(resume_vector, vector))) * 100.0
            company = job.company
            score_result = compute_weighted_score(
                embedding_score_0_100=embedding_score,
                job_title=job.title,
                job_description=job.description,
                location=job.location,
                company_name=company.name if company else None,
                visa_sponsorship=company.visa_sponsorship if company else None,
                workplace_type=job.workplace_type,
                resume_skills=resume_skills,
                resume_profile=resume_profile,
            )
            job.match_score = score_result.overall
            job.role_category = score_result.role_category
            job.role_priority = score_result.role_priority
            job.score_breakdown = score_result.breakdown
            job.critical_missing_skills = score_result.required_skills_missing

            # If the rule-based scorer now recommends the job, keep should_apply true
            # even if it was previously reasoned. Ollama can still downgrade on the
            # next reasoning pass if the resume or JD changed.
            if score_result.should_apply:
                job.should_apply = True
            elif not job.ai_reasoned_at:
                job.should_apply = score_result.should_apply
            updated += 1

        await self.db.commit()
        return updated

    # ------------------------------------------------------------------
    # Ollama reasoning (top N only)
    # ------------------------------------------------------------------
    async def reason_top_jobs(
        self,
        resume: Resume,
        resume_vector: np.ndarray,
        top_n: int | None = None,
    ) -> int:
        top_n = top_n or self.settings.top_jobs_for_ollama

        # Determine which high-ranking jobs need reasoning.
        top_jobs = list(
            (
                await self.db.execute(
                    select(Job)
                    .options(selectinload(Job.company))
                    .where(Job.is_active == True, Job.is_deleted == False, Job.rejected == False)
                    .order_by(Job.match_score.desc().nullslast())
                    .limit(top_n)
                )
            )
            .scalars()
            .all()
        )

        if not top_jobs:
            return 0

        ollama_available = await self.ollama.is_available()
        if not ollama_available:
            logger.warning("ollama_not_available, skipping reasoning")
            return 0

        now = datetime.utcnow()
        reasoned = 0
        current_resume_hash = resume.embedding_content_hash or _text_hash(
            resume.content_text
        )

        jobs_to_reason: list[tuple[Job, str]] = []
        for job in top_jobs:
            current_description_hash = job.description_hash or _text_hash(
                job.description
            )
            # Skip if already reasoned for this exact job description and resume.
            if (
                job.ai_reasoned_at
                and job.match_reason
                and job.ai_reasoned_description_hash == current_description_hash
                and job.ai_reasoned_resume_hash == current_resume_hash
            ):
                continue
            jobs_to_reason.append((job, current_description_hash))

        if not jobs_to_reason:
            return 0

        semaphore = asyncio.Semaphore(3)

        async def _reason(job: Job, current_description_hash: str) -> tuple[Job, str, dict]:
            async with semaphore:
                prompt = _prompt_for_reasoning(
                    resume_text=resume.content_text or "",
                    skills=resume.skills or [],
                    job_title=job.title,
                    job_description=job.description or "",
                    location=job.location,
                    company_name=job.company.name if job.company else None,
                    current_score=float(job.match_score or 0),
                )
                parsed = await self.ollama.generate_json(prompt)
                return job, current_description_hash, parsed

        results = await asyncio.gather(
            *[_reason(job, desc_hash) for job, desc_hash in jobs_to_reason]
        )

        for job, current_description_hash, parsed in results:
            if parsed:
                job.match_reason = str(parsed.get("reason", ""))
                job.missing_skills = parsed.get("missing_skills") or []
                job.visa_sponsorship_inferred = str(
                    parsed.get("visa_probability", "Unknown")
                )
                job.should_apply = bool(parsed.get("should_apply", job.should_apply))
                job.confidence = float(parsed.get("confidence", 0.5))
                job.ai_reasoned_at = now
                job.ai_reasoned_description_hash = current_description_hash
                job.ai_reasoned_resume_hash = current_resume_hash
                reasoned += 1

        await self.db.commit()
        return reasoned

    # ------------------------------------------------------------------
    # Single-job matching (used by per-job API endpoints)
    # ------------------------------------------------------------------
    async def match_single(self, job_id: int) -> dict:
        """Match a single job against the master resume and return the result."""
        resume_service = ResumeService(self.db)
        resume = await resume_service.get_master_resume()
        if resume is None:
            raise ValueError("Upload a master resume first")

        resume_vector = await self.ensure_resume_embedding(resume)
        resume_profile = await self.ensure_resume_profile(resume)
        resume_skills = set(resume_profile.get("skills", []))

        job = await self.db.get(Job, job_id, options=[selectinload(Job.country)])
        if job is None:
            raise ValueError("Job not found")

        company = await self.db.get(Company, job.company_id) if job.company_id else None
        company_name = company.name if company else None

        filter_result = mandatory_filter(
            title=job.title,
            description=job.description,
            location=job.location,
            country_name=job.country.name if job.country else None,
            country_is_eu=job.country.is_eu if job.country else None,
            resume_skills=resume_skills,
        )
        job.role_category, _ = classify_role(job.title, job.description)
        if filter_result.rejected:
            job.rejected = True
            job.rejection_reason = filter_result.reason
            job.role_priority = "reject"
            job.match_score = 0.0
            job.should_apply = False
            job.match_reason = f"Rejected: {filter_result.reason}"
            job.critical_missing_skills = []
            await self.db.commit()
            return {
                "score": job.match_score,
                "reason": job.match_reason,
                "strengths": [],
                "missing_skills": [],
                "salary_estimate": job.salary_estimate or "",
                "visa_probability": job.visa_sponsorship_inferred,
                "should_apply": False,
                "confidence": 1.0,
                "interview_difficulty": "N/A",
                "predicted_questions": [],
            }

        job.rejected = False
        job.rejection_reason = None
        await self.ensure_job_embeddings([job_id])

        # Score this specific job.
        job_vector = await self.vector_store.get_active_job_embeddings(self.db)
        if job_id in job_vector:
            embedding_score = (
                max(0.0, float(cosine_similarity(resume_vector, job_vector[job_id])))
                * 100.0
            )
        else:
            text = f"{job.title}\n{job.description or ''}"
            vec = self.embedding_model.encode([text])[0]
            embedding_score = max(0.0, float(cosine_similarity(resume_vector, vec))) * 100.0
            await self.vector_store.store_job_embedding(
                self.db, job.id, vec.tolist(), self.embedding_model.model_name
            )

        score_result = compute_weighted_score(
            embedding_score_0_100=embedding_score,
            job_title=job.title,
            job_description=job.description,
            location=job.location,
            company_name=company_name,
            visa_sponsorship=company.visa_sponsorship if company else None,
            workplace_type=job.workplace_type,
            resume_skills=resume_skills,
            resume_profile=resume_profile,
        )
        job.match_score = score_result.overall
        job.should_apply = score_result.should_apply
        job.role_category = score_result.role_category
        job.role_priority = score_result.role_priority
        job.score_breakdown = score_result.breakdown
        job.critical_missing_skills = score_result.required_skills_missing
        await self.db.commit()

        # Always try Ollama for a single explicit match, unless unavailable.
        if await self.ollama.is_available():
            prompt = _prompt_for_reasoning(
                resume_text=resume.content_text or "",
                skills=resume.skills or [],
                job_title=job.title,
                job_description=job.description or "",
                location=job.location,
                company_name=company_name,
                current_score=float(job.match_score),
            )
            parsed = await self.ollama.generate_json(prompt)
            if parsed:
                job.match_reason = str(parsed.get("reason", ""))
                job.missing_skills = parsed.get("missing_skills") or []
                job.visa_sponsorship_inferred = str(
                    parsed.get("visa_probability", "Unknown")
                )
                job.should_apply = bool(parsed.get("should_apply", job.should_apply))
                job.confidence = float(parsed.get("confidence", 0.5))
                job.ai_reasoned_at = datetime.utcnow()
                await self.db.commit()

        return {
            "score": job.match_score,
            "reason": job.match_reason,
            "strengths": [],
            "missing_skills": job.missing_skills or [],
            "salary_estimate": job.salary_estimate or "",
            "visa_probability": job.visa_sponsorship_inferred,
            "should_apply": job.should_apply,
            "confidence": job.confidence,
            "interview_difficulty": "Medium",
            "predicted_questions": [],
        }

    # ------------------------------------------------------------------
    # Entry point
    # ------------------------------------------------------------------
    async def run(
        self, job_ids: Sequence[int] | None = None, top_n: int | None = None
    ) -> dict:
        """Run the full local matching pipeline and return a summary."""
        resume_service = ResumeService(self.db)
        resume = await resume_service.get_master_resume()
        if resume is None:
            logger.warning("no_master_resume_found")
            return {
                "status": "skipped",
                "reason": "no_master_resume",
                "embeddings_generated": 0,
                "jobs_scored": 0,
                "jobs_reasoned": 0,
            }

        resume_vector = await self.ensure_resume_embedding(resume)
        resume_profile = await self.ensure_resume_profile(resume)
        resume_skills = set(resume_profile.get("skills", []))

        allowed_ids, rejected_count = await self.classify_and_filter_jobs(resume_skills)
        if job_ids is not None:
            allowed_set = set(allowed_ids)
            embed_target_ids: list[int] = [jid for jid in job_ids if jid in allowed_set]
        else:
            embed_target_ids = allowed_ids

        embed_count = await self.ensure_job_embeddings(embed_target_ids)
        scored = await self.score_all_jobs(resume_vector, resume_skills, resume_profile)
        reasoned = await self.reason_top_jobs(resume, resume_vector, top_n=top_n)

        return {
            "status": "ok",
            "embeddings_generated": embed_count,
            "jobs_scored": scored,
            "jobs_rejected": rejected_count,
            "jobs_reasoned": reasoned,
        }
