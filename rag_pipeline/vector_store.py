"""Qdrant Vector Database Service - stores and searches vector embeddings."""

from typing import Optional
import uuid

from qdrant_client import QdrantClient, models

from rag_pipeline.config import settings

# Collection names
RESUME_COLLECTION = "resumes"
JOB_COLLECTION = "jobs"

# Embedding dimension (all-MiniLM-L6-v2 = 384 dimensions)
EMBEDDING_DIM = 384


class VectorStore:
    """Qdrant vector database wrapper."""

    def __init__(self):
        self._client: Optional[QdrantClient] = None

    @property
    def client(self) -> QdrantClient:
        """Lazy-initialize Qdrant client. Falls back to in-memory if server unavailable."""
        if self._client is None:
            try:
                host = getattr(settings, "QDRANT_HOST", "localhost")
                port = int(getattr(settings, "QDRANT_PORT", 6333))
                client = QdrantClient(host=host, port=port, timeout=3)
                client.get_collections()
                self._client = client
            except Exception:
                # Fallback to in-memory for development/testing
                self._client = QdrantClient(":memory:")
        return self._client

    def ensure_collections(self):
        """Create collections if they don't exist."""
        collections = [c.name for c in self.client.get_collections().collections]

        if RESUME_COLLECTION not in collections:
            self.client.create_collection(
                collection_name=RESUME_COLLECTION,
                vectors_config=models.VectorParams(size=EMBEDDING_DIM, distance=models.Distance.COSINE),
            )

        if JOB_COLLECTION not in collections:
            self.client.create_collection(
                collection_name=JOB_COLLECTION,
                vectors_config=models.VectorParams(size=EMBEDDING_DIM, distance=models.Distance.COSINE),
            )

    def upsert_resume(
        self,
        resume_id: int,
        candidate_id: int,
        embedding: list[float],
        metadata: dict = None,
    ) -> str:
        """Store or update a resume embedding."""
        self.ensure_collections()
        point_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"resume_{resume_id}"))

        payload = {
            "resume_id": resume_id,
            "candidate_id": candidate_id,
            **(metadata or {}),
        }

        self.client.upsert(
            collection_name=RESUME_COLLECTION,
            points=[
                models.PointStruct(id=point_id, vector=embedding, payload=payload)
            ],
        )
        return point_id

    def upsert_job(
        self,
        job_id: int,
        embedding: list[float],
        metadata: dict = None,
    ) -> str:
        """Store or update a job embedding."""
        self.ensure_collections()
        point_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"job_{job_id}"))

        payload = {"job_id": job_id, **(metadata or {})}

        self.client.upsert(
            collection_name=JOB_COLLECTION,
            points=[
                models.PointStruct(id=point_id, vector=embedding, payload=payload)
            ],
        )
        return point_id

    def search_similar_resumes(
        self,
        query_vector: list[float],
        top_k: int = 10,
        score_threshold: float = 0.0,
    ) -> list[dict]:
        """Search for similar resumes using vector similarity."""
        self.ensure_collections()
        results = self.client.query_points(
            collection_name=RESUME_COLLECTION,
            query=query_vector,
            limit=top_k,
            score_threshold=score_threshold,
        )

        return [
            {
                "candidate_id": hit.payload.get("candidate_id"),
                "resume_id": hit.payload.get("resume_id"),
                "similarity_score": round(hit.score * 100, 2),
                "metadata": hit.payload,
            }
            for hit in results.points
        ]

    def search_similar_jobs(
        self,
        query_vector: list[float],
        top_k: int = 5,
    ) -> list[dict]:
        """Search for similar jobs using vector similarity."""
        self.ensure_collections()
        results = self.client.query_points(
            collection_name=JOB_COLLECTION,
            query=query_vector,
            limit=top_k,
        )

        return [
            {
                "job_id": hit.payload.get("job_id"),
                "similarity_score": round(hit.score * 100, 2),
                "metadata": hit.payload,
            }
            for hit in results.points
        ]

    def get_collection_info(self, collection_name: str) -> dict:
        """Get collection statistics."""
        try:
            info = self.client.get_collection(collection_name)
            return {
                "name": collection_name,
                "vectors_count": info.vectors_count,
                "points_count": info.points_count,
            }
        except Exception:
            return {"name": collection_name, "vectors_count": 0, "points_count": 0}

    def delete_resume(self, resume_id: int):
        """Delete a resume embedding."""
        point_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"resume_{resume_id}"))
        self.client.delete(
            collection_name=RESUME_COLLECTION,
            points_selector=[point_id],
        )


# Singleton instance
vector_store = VectorStore()
