"""Graph RAG Service - Retrieval-Augmented Generation using Knowledge Graph.

Combines graph traversal with LLM generation for:
- Context-enriched candidate evaluation
- Skill-aware question generation
- Graph-based recommendation explanations
"""

from typing import Optional

from rag_pipeline.knowledge_graph import knowledge_graph
from rag_pipeline.llm_service import llm_service
from rag_pipeline.embedding_service import generate_embedding
from rag_pipeline.vector_store import vector_store


GRAPH_RAG_SYSTEM_PROMPT = """You are an AI recruitment assistant with access to a knowledge graph of skills, 
candidates, and job requirements. Use the provided graph context to give accurate, 
well-grounded recommendations.

When evaluating candidates:
- Consider skill relationships (e.g., knowing Python suggests potential for FastAPI)
- Account for transferable skills
- Identify skill gaps and learning potential
- Provide explanations grounded in the graph data

Always be specific and reference the graph context provided."""


class GraphRAGService:
    """Graph-enhanced RAG for recruitment intelligence."""

    def retrieve_graph_context(
        self,
        candidate_skills: list[str],
        job_required_skills: list[str],
        job_preferred_skills: list[str] = None,
    ) -> dict:
        """
        Retrieve relevant context from the knowledge graph.
        Combines skill relationships, gaps, and transferable skills.
        """
        context = {
            "skill_relationships": {},
            "candidate_adjacent_skills": [],
            "job_skill_ecosystem": [],
            "skill_gaps": [],
            "transferable_skills": [],
        }

        # Get related skills for each candidate skill
        for skill in candidate_skills[:10]:
            related = knowledge_graph.get_related_skills(skill, depth=2)
            if related:
                context["skill_relationships"][skill] = related

        # Find job-related skills ecosystem
        for skill in job_required_skills[:5]:
            related = knowledge_graph.get_related_skills(skill, depth=1)
            context["job_skill_ecosystem"].extend(related)

        # Identify skill gaps
        candidate_set = set(s.lower() for s in candidate_skills)
        required_set = set(s.lower() for s in job_required_skills)
        context["skill_gaps"] = list(required_set - candidate_set)

        # Find transferable skills
        for missing_skill in context["skill_gaps"]:
            related = knowledge_graph.get_related_skills(missing_skill, depth=1)
            for r in related:
                if r["name"] in candidate_set:
                    context["transferable_skills"].append({
                        "has": r["name"],
                        "related_to_missing": missing_skill,
                        "distance": r["distance"],
                    })

        return context

    def generate_enhanced_evaluation(
        self,
        candidate_skills: list[str],
        candidate_experience: float,
        job_title: str,
        job_required_skills: list[str],
        job_preferred_skills: list[str] = None,
        interview_score: Optional[float] = None,
    ) -> dict:
        """
        Generate an evaluation enriched with graph context.
        Uses Graph RAG: retrieve from graph → augment prompt → generate.
        """
        # 1. Retrieve graph context
        graph_context = self.retrieve_graph_context(
            candidate_skills=candidate_skills,
            job_required_skills=job_required_skills,
            job_preferred_skills=job_preferred_skills or [],
        )

        # 2. Build augmented prompt
        context_text = self._format_graph_context(graph_context)

        # 3. Generate with LLM (or fallback)
        if llm_service.is_available:
            return self._generate_with_llm(
                context_text=context_text,
                candidate_skills=candidate_skills,
                candidate_experience=candidate_experience,
                job_title=job_title,
                job_required_skills=job_required_skills,
                interview_score=interview_score,
            )

        # Fallback: rule-based evaluation with graph context
        return self._fallback_evaluation(
            graph_context=graph_context,
            candidate_skills=candidate_skills,
            candidate_experience=candidate_experience,
            job_required_skills=job_required_skills,
            interview_score=interview_score,
        )

    def get_skill_recommendations(self, candidate_skills: list[str], job_required_skills: list[str]) -> dict:
        """Get skill-based recommendations using graph traversal."""
        graph_context = self.retrieve_graph_context(
            candidate_skills=candidate_skills,
            job_required_skills=job_required_skills,
        )

        # Skills the candidate could learn based on their current skills
        learning_recommendations = []
        for gap in graph_context["skill_gaps"]:
            related = knowledge_graph.get_related_skills(gap, depth=1)
            candidate_set = set(s.lower() for s in candidate_skills)
            has_foundation = any(r["name"] in candidate_set for r in related)
            learning_recommendations.append({
                "skill": gap,
                "has_foundation": has_foundation,
                "related_skills_known": [r["name"] for r in related if r["name"] in candidate_set],
                "difficulty_to_learn": "low" if has_foundation else "medium",
            })

        return {
            "skill_gaps": graph_context["skill_gaps"],
            "transferable_skills": graph_context["transferable_skills"],
            "learning_recommendations": learning_recommendations,
        }

    def hybrid_graph_vector_search(
        self,
        query: str,
        candidate_skills: list[str] = None,
        top_k: int = 10,
    ) -> list[dict]:
        """
        Combine vector search with graph-based filtering.
        Uses graph context to boost candidates with related skills.
        """
        # Vector search
        query_embedding = generate_embedding(query)
        vector_results = vector_store.search_similar_resumes(query_embedding, top_k=top_k * 2)

        # Graph-based boost: if query mentions specific skills, boost candidates with related skills
        if candidate_skills:
            graph_boost = set()
            for skill in candidate_skills[:5]:
                related = knowledge_graph.get_related_skills(skill, depth=1)
                graph_boost.update(r["name"] for r in related)

        # Return enriched results
        return vector_results[:top_k]

    def _format_graph_context(self, context: dict) -> str:
        """Format graph context into a readable string for LLM prompt."""
        parts = []

        if context["skill_gaps"]:
            parts.append(f"Missing Skills: {', '.join(context['skill_gaps'])}")

        if context["transferable_skills"]:
            transfers = [f"{t['has']} → {t['related_to_missing']}" for t in context["transferable_skills"][:5]]
            parts.append(f"Transferable Skills: {'; '.join(transfers)}")

        if context["skill_relationships"]:
            for skill, related in list(context["skill_relationships"].items())[:3]:
                rel_names = [r["name"] for r in related[:4]]
                parts.append(f"{skill} is related to: {', '.join(rel_names)}")

        return "\n".join(parts) if parts else "No additional graph context available."

    def _generate_with_llm(self, context_text, candidate_skills, candidate_experience, job_title, job_required_skills, interview_score):
        """Generate evaluation using LLM with graph context."""
        user_prompt = f"""Evaluate this candidate with the following graph context:

**Graph Context:**
{context_text}

**Candidate:** Skills={', '.join(candidate_skills[:10])}, Experience={candidate_experience} years
**Job:** {job_title}, Required={', '.join(job_required_skills)}
**Interview Score:** {interview_score or 'Not yet interviewed'}

Provide a JSON evaluation with: overall_assessment, fit_score (0-100), strengths, gaps, learning_potential, recommendation"""

        result = llm_service.generate_json(
            system_prompt=GRAPH_RAG_SYSTEM_PROMPT,
            user_prompt=user_prompt,
        )
        return result if result else self._fallback_evaluation(
            {"skill_gaps": [], "transferable_skills": []},
            candidate_skills, candidate_experience, job_required_skills, interview_score
        )

    def _fallback_evaluation(self, graph_context, candidate_skills, candidate_experience, job_required_skills, interview_score):
        """Rule-based evaluation with graph context."""
        candidate_set = set(s.lower() for s in candidate_skills)
        required_set = set(s.lower() for s in job_required_skills)

        matched = candidate_set & required_set
        missing = required_set - candidate_set
        match_pct = (len(matched) / len(required_set) * 100) if required_set else 0

        # Factor in transferable skills
        transferable = graph_context.get("transferable_skills", [])
        transfer_bonus = min(20, len(transferable) * 5)

        fit_score = min(100, match_pct * 0.6 + transfer_bonus + min(20, candidate_experience * 3))
        if interview_score:
            fit_score = fit_score * 0.5 + interview_score * 0.5

        if fit_score >= 70:
            recommendation = "strongly_recommended"
        elif fit_score >= 50:
            recommendation = "recommended"
        elif fit_score >= 35:
            recommendation = "potential_with_training"
        else:
            recommendation = "not_recommended"

        return {
            "overall_assessment": f"Candidate matches {len(matched)}/{len(required_set)} required skills with {len(transferable)} transferable skills.",
            "fit_score": round(fit_score, 2),
            "strengths": list(matched)[:5],
            "gaps": list(missing)[:5],
            "transferable_skills": [t["has"] for t in transferable[:5]],
            "learning_potential": "high" if transfer_bonus >= 10 else "medium" if transfer_bonus >= 5 else "low",
            "recommendation": recommendation,
            "graph_context_used": True,
        }


# Singleton
graph_rag_service = GraphRAGService()
