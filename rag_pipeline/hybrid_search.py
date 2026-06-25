"""Hybrid Search Service - combines BM25 lexical search with vector semantic search."""

from typing import Optional

from rag_pipeline.jd_matcher import jd_matcher, preprocess_text, calculate_skill_match_score
from rag_pipeline.embedding_service import generate_embedding, prepare_resume_text_for_embedding
from rag_pipeline.vector_store import vector_store


class HybridSearchEngine:
    """
    Combines BM25 (lexical) and vector (semantic) search with configurable weights.
    
    Hybrid Score = (bm25_weight * bm25_score) + (vector_weight * vector_score) + (skill_weight * skill_score)
    """

    def __init__(
        self,
        bm25_weight: float = 0.35,
        vector_weight: float = 0.45,
        skill_weight: float = 0.20,
    ):
        self.bm25_weight = bm25_weight
        self.vector_weight = vector_weight
        self.skill_weight = skill_weight

    def search(
        self,
        query: str,
        required_skills: list[str] = None,
        top_k: int = 10,
        use_bm25: bool = True,
        use_vector: bool = True,
    ) -> list[dict]:
        """
        Perform hybrid search combining BM25 + vector similarity + skill matching.
        
        Args:
            query: Natural language search query or job description
            required_skills: Optional skill list for skill-based boosting
            top_k: Number of results to return
            use_bm25: Enable/disable BM25 component
            use_vector: Enable/disable vector component
        
        Returns:
            Ranked list of candidates with scores
        """
        candidate_scores: dict[int, dict] = {}

        # 1. BM25 Lexical Search
        if use_bm25:
            bm25_results = jd_matcher.search(query, top_k=top_k * 2)
            for result in bm25_results:
                cid = result["candidate_id"]
                if cid not in candidate_scores:
                    candidate_scores[cid] = {"bm25_score": 0, "vector_score": 0, "skill_score": 0}
                candidate_scores[cid]["bm25_score"] = result["bm25_score"]

        # 2. Vector Semantic Search
        if use_vector:
            query_embedding = generate_embedding(query)
            vector_results = vector_store.search_similar_resumes(
                query_vector=query_embedding,
                top_k=top_k * 2,
            )
            for result in vector_results:
                cid = result["candidate_id"]
                if cid not in candidate_scores:
                    candidate_scores[cid] = {"bm25_score": 0, "vector_score": 0, "skill_score": 0}
                candidate_scores[cid]["vector_score"] = result["similarity_score"]
                # Capture candidate skills from vector metadata so skill matching can use them
                metadata = result.get("metadata") or {}
                if metadata.get("skills"):
                    candidate_scores[cid]["skills"] = metadata["skills"]

        # 3. Skill Matching (if skills provided)
        if required_skills:
            for cid, scores in candidate_scores.items():
                # Get candidate skills from metadata (stored during indexing)
                candidate_skills = scores.get("skills", [])
                if candidate_skills:
                    skill_result = calculate_skill_match_score(
                        candidate_skills, required_skills
                    )
                    scores["skill_score"] = skill_result["score"]

        # 4. Calculate hybrid scores
        results = []
        for cid, scores in candidate_scores.items():
            hybrid_score = (
                self.bm25_weight * scores["bm25_score"]
                + self.vector_weight * scores["vector_score"]
                + self.skill_weight * scores["skill_score"]
            )
            results.append({
                "candidate_id": cid,
                "hybrid_score": round(hybrid_score, 2),
                "bm25_score": round(scores["bm25_score"], 2),
                "vector_score": round(scores["vector_score"], 2),
                "skill_score": round(scores["skill_score"], 2),
            })

        # Sort by hybrid score
        results.sort(key=lambda x: x["hybrid_score"], reverse=True)
        return results[:top_k]

    def index_candidate(
        self,
        candidate_id: int,
        resume_id: int,
        skills: list[str],
        experience_years: float,
        raw_text: str,
    ) -> str:
        """Index a candidate in the vector store."""
        text = prepare_resume_text_for_embedding(skills, experience_years, raw_text)
        embedding = generate_embedding(text)
        point_id = vector_store.upsert_resume(
            resume_id=resume_id,
            candidate_id=candidate_id,
            embedding=embedding,
            metadata={
                "skills": skills,
                "experience_years": experience_years,
            },
        )
        return point_id

    def index_job(self, job_id: int, title: str, description: str, required_skills: list[str], preferred_skills: list[str]) -> str:
        """Index a job in the vector store."""
        from rag_pipeline.embedding_service import prepare_job_text_for_embedding
        text = prepare_job_text_for_embedding(title, description, required_skills, preferred_skills)
        embedding = generate_embedding(text)
        point_id = vector_store.upsert_job(
            job_id=job_id,
            embedding=embedding,
            metadata={"title": title, "required_skills": required_skills},
        )
        return point_id


# Singleton
hybrid_search = HybridSearchEngine()
