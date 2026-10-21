"""Vector storage abstraction.

The public interface is backend-agnostic. The default implementation stores
embeddings as JSONB in Postgres and computes cosine similarity in Python.
A pgvector backend can be enabled by setting `VECTOR_BACKEND=pgvector`.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Sequence

import numpy as np
import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings

logger = structlog.get_logger()


class VectorBackend(ABC):
    """Backend-agnostic interface for storing and querying embeddings."""

    @abstractmethod
    async def store_job_embedding(
        self,
        db: AsyncSession,
        job_id: int,
        vector: Sequence[float],
        model_name: str,
    ) -> None:
        ...

    @abstractmethod
    async def store_resume_embedding(
        self,
        db: AsyncSession,
        resume_id: int,
        vector: Sequence[float],
        model_name: str,
    ) -> None:
        ...

    @abstractmethod
    async def get_resume_embedding(
        self, db: AsyncSession, resume_id: int
    ) -> np.ndarray | None:
        ...

    @abstractmethod
    async def get_active_job_embeddings(
        self, db: AsyncSession
    ) -> dict[int, np.ndarray]:
        """Return a mapping from active job IDs to their embeddings."""
        ...


class NumpyBackend(VectorBackend):
    """Cosine-similarity backend using JSONB-stored vectors and NumPy."""

    async def store_job_embedding(
        self,
        db: AsyncSession,
        job_id: int,
        vector: Sequence[float],
        model_name: str,
    ) -> None:
        from app.models.job import Job

        job = await db.get(Job, job_id)
        if job is None:
            return
        job.embedding = list(vector)
        job.embedding_model = model_name

    async def store_resume_embedding(
        self,
        db: AsyncSession,
        resume_id: int,
        vector: Sequence[float],
        model_name: str,
    ) -> None:
        from app.models.resume import Resume

        resume = await db.get(Resume, resume_id)
        if resume is None:
            return
        resume.embedding = list(vector)
        resume.embedding_model = model_name

    async def get_resume_embedding(
        self, db: AsyncSession, resume_id: int
    ) -> np.ndarray | None:
        from app.models.resume import Resume

        resume = await db.get(Resume, resume_id)
        if resume is None or resume.embedding is None:
            return None
        return np.asarray(resume.embedding, dtype=np.float32)

    async def get_active_job_embeddings(
        self, db: AsyncSession
    ) -> dict[int, np.ndarray]:
        from app.models.job import Job

        result = await db.execute(
            select(Job.id, Job.embedding).where(
                Job.is_active == True, Job.is_deleted == False, Job.embedding.is_not(None)
            )
        )
        return {
            row.id: np.asarray(row.embedding, dtype=np.float32)
            for row in result.all()
            if row.embedding is not None
        }


class PGVectorBackend(VectorBackend):
    """pgvector backend using the `pgvector` SQLAlchemy type.

    This requires the `vector` Postgres extension and a `vector(N)` column
    on the `jobs` and `resumes` tables.
    """

    async def _get_dimension(self) -> int:
        from app.ai.embeddings import get_embedding_model

        return get_embedding_model().dimension

    async def store_job_embedding(
        self,
        db: AsyncSession,
        job_id: int,
        vector: Sequence[float],
        model_name: str,
    ) -> None:
        from app.models.job import Job

        job = await db.get(Job, job_id)
        if job is None:
            return
        # PGVector columns expect a list/sequence of floats
        job.embedding = list(vector)
        job.embedding_model = model_name

    async def store_resume_embedding(
        self,
        db: AsyncSession,
        resume_id: int,
        vector: Sequence[float],
        model_name: str,
    ) -> None:
        from app.models.resume import Resume

        resume = await db.get(Resume, resume_id)
        if resume is None:
            return
        resume.embedding = list(vector)
        resume.embedding_model = model_name

    async def get_resume_embedding(
        self, db: AsyncSession, resume_id: int
    ) -> np.ndarray | None:
        from app.models.resume import Resume

        resume = await db.get(Resume, resume_id)
        if resume is None or resume.embedding is None:
            return None
        return np.asarray(resume.embedding, dtype=np.float32)

    async def get_active_job_embeddings(
        self, db: AsyncSession
    ) -> dict[int, np.ndarray]:
        from app.models.job import Job

        result = await db.execute(
            select(Job.id, Job.embedding).where(
                Job.is_active == True, Job.is_deleted == False, Job.embedding.is_not(None)
            )
        )
        return {
            row.id: np.asarray(row.embedding, dtype=np.float32)
            for row in result.all()
            if row.embedding is not None
        }


def create_vector_backend() -> VectorBackend:
    backend = (get_settings().vector_backend or "numpy").lower()
    if backend == "pgvector":
        return PGVectorBackend()
    if backend == "numpy":
        return NumpyBackend()
    logger.warning("unknown_vector_backend", backend=backend, fallback="numpy")
    return NumpyBackend()
