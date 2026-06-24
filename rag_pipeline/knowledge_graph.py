"""Knowledge Graph Service - Neo4j integration for skill relationships.

Builds and queries a knowledge graph of:
- Skills and their relationships
- Candidates and their skill sets
- Jobs and their requirements
- Skill hierarchies and prerequisites
"""

from typing import Optional

from app.core.config import settings


class KnowledgeGraphService:
    """Neo4j-based knowledge graph for recruitment intelligence."""

    def __init__(self):
        self._driver = None
        self.neo4j_uri = getattr(settings, "NEO4J_URI", "bolt://localhost:7687")
        self.neo4j_user = getattr(settings, "NEO4J_USER", "neo4j")
        self.neo4j_password = getattr(settings, "NEO4J_PASSWORD", "")

    @property
    def driver(self):
        """Lazy-initialize Neo4j driver."""
        if self._driver is None and self.neo4j_password:
            from neo4j import GraphDatabase
            self._driver = GraphDatabase.driver(
                self.neo4j_uri,
                auth=(self.neo4j_user, self.neo4j_password),
            )
        return self._driver

    @property
    def is_available(self) -> bool:
        """Check if Neo4j is configured and accessible."""
        if not self.neo4j_password:
            return False
        try:
            if self.driver:
                self.driver.verify_connectivity()
                return True
        except Exception:
            pass
        return False

    def close(self):
        """Close the Neo4j driver."""
        if self._driver:
            self._driver.close()

    # --- Schema Creation ---

    def create_schema(self):
        """Create graph schema constraints and indexes."""
        if not self.is_available:
            return {"status": "unavailable"}

        with self.driver.session() as session:
            session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (s:Skill) REQUIRE s.name IS UNIQUE")
            session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (c:Candidate) REQUIRE c.id IS UNIQUE")
            session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (j:Job) REQUIRE j.id IS UNIQUE")
            session.run("CREATE INDEX IF NOT EXISTS FOR (s:Skill) ON (s.category)")

        return {"status": "schema_created"}

    # --- Skill Graph ---

    def add_skill(self, name: str, category: str = "general", level: str = "intermediate"):
        """Add a skill node to the graph."""
        if not self.is_available:
            return None
        with self.driver.session() as session:
            result = session.run(
                "MERGE (s:Skill {name: $name}) "
                "SET s.category = $category, s.level = $level "
                "RETURN s",
                name=name.lower(), category=category, level=level,
            )
            return result.single()

    def add_skill_relationship(self, skill1: str, skill2: str, relationship: str = "RELATED_TO"):
        """Create a relationship between two skills."""
        if not self.is_available:
            return None
        with self.driver.session() as session:
            query = (
                f"MATCH (s1:Skill {{name: $skill1}}) "
                f"MATCH (s2:Skill {{name: $skill2}}) "
                f"MERGE (s1)-[r:{relationship}]->(s2) "
                f"RETURN s1, r, s2"
            )
            return session.run(query, skill1=skill1.lower(), skill2=skill2.lower())

    def add_candidate_skills(self, candidate_id: int, skills: list[str]):
        """Link a candidate to their skills in the graph."""
        if not self.is_available:
            return None
        with self.driver.session() as session:
            session.run(
                "MERGE (c:Candidate {id: $id})",
                id=candidate_id,
            )
            for skill in skills:
                session.run(
                    "MATCH (c:Candidate {id: $cid}) "
                    "MERGE (s:Skill {name: $skill}) "
                    "MERGE (c)-[:HAS_SKILL]->(s)",
                    cid=candidate_id, skill=skill.lower(),
                )

    def add_job_requirements(self, job_id: int, required_skills: list[str], preferred_skills: list[str] = None):
        """Link a job to its required/preferred skills."""
        if not self.is_available:
            return None
        with self.driver.session() as session:
            session.run("MERGE (j:Job {id: $id})", id=job_id)
            for skill in required_skills:
                session.run(
                    "MATCH (j:Job {id: $jid}) "
                    "MERGE (s:Skill {name: $skill}) "
                    "MERGE (j)-[:REQUIRES]->(s)",
                    jid=job_id, skill=skill.lower(),
                )
            for skill in (preferred_skills or []):
                session.run(
                    "MATCH (j:Job {id: $jid}) "
                    "MERGE (s:Skill {name: $skill}) "
                    "MERGE (j)-[:PREFERS]->(s)",
                    jid=job_id, skill=skill.lower(),
                )

    # --- Graph Queries ---

    def get_related_skills(self, skill: str, depth: int = 2) -> list[dict]:
        """Find skills related to a given skill within N hops."""
        if not self.is_available:
            return self._fallback_related_skills(skill)

        with self.driver.session() as session:
            result = session.run(
                "MATCH (s:Skill {name: $skill})-[r*1..$depth]-(related:Skill) "
                "RETURN DISTINCT related.name AS name, related.category AS category, "
                "length(r) AS distance "
                "ORDER BY distance "
                "LIMIT 20",
                skill=skill.lower(), depth=depth,
            )
            return [{"name": r["name"], "category": r["category"], "distance": r["distance"]}
                    for r in result]

    def get_candidates_with_skill(self, skill: str) -> list[dict]:
        """Find candidates who have a specific skill."""
        if not self.is_available:
            return []
        with self.driver.session() as session:
            result = session.run(
                "MATCH (c:Candidate)-[:HAS_SKILL]->(s:Skill {name: $skill}) "
                "RETURN c.id AS candidate_id",
                skill=skill.lower(),
            )
            return [{"candidate_id": r["candidate_id"]} for r in result]

    def get_skill_gap(self, candidate_id: int, job_id: int) -> dict:
        """Analyze skill gap between a candidate and job requirements."""
        if not self.is_available:
            return {"status": "unavailable"}

        with self.driver.session() as session:
            # Skills the candidate has that the job requires
            matched = session.run(
                "MATCH (c:Candidate {id: $cid})-[:HAS_SKILL]->(s:Skill)<-[:REQUIRES]-(j:Job {id: $jid}) "
                "RETURN collect(s.name) AS matched_skills",
                cid=candidate_id, jid=job_id,
            ).single()

            # Skills the job requires that candidate lacks
            missing = session.run(
                "MATCH (j:Job {id: $jid})-[:REQUIRES]->(s:Skill) "
                "WHERE NOT EXISTS { MATCH (c:Candidate {id: $cid})-[:HAS_SKILL]->(s) } "
                "RETURN collect(s.name) AS missing_skills",
                cid=candidate_id, jid=job_id,
            ).single()

            # Related skills the candidate has (potential transferable)
            transferable = session.run(
                "MATCH (j:Job {id: $jid})-[:REQUIRES]->(req:Skill)-[:RELATED_TO]-(related:Skill)<-[:HAS_SKILL]-(c:Candidate {id: $cid}) "
                "WHERE NOT EXISTS { MATCH (c)-[:HAS_SKILL]->(req) } "
                "RETURN DISTINCT related.name AS skill, req.name AS related_to",
                cid=candidate_id, jid=job_id,
            )

            return {
                "matched_skills": matched["matched_skills"] if matched else [],
                "missing_skills": missing["missing_skills"] if missing else [],
                "transferable_skills": [
                    {"skill": r["skill"], "related_to": r["related_to"]}
                    for r in transferable
                ],
            }

    def find_similar_candidates(self, candidate_id: int, min_shared_skills: int = 3) -> list[dict]:
        """Find candidates with similar skill profiles."""
        if not self.is_available:
            return []
        with self.driver.session() as session:
            result = session.run(
                "MATCH (c1:Candidate {id: $cid})-[:HAS_SKILL]->(s:Skill)<-[:HAS_SKILL]-(c2:Candidate) "
                "WHERE c1 <> c2 "
                "WITH c2, collect(s.name) AS shared, count(s) AS cnt "
                "WHERE cnt >= $min_shared "
                "RETURN c2.id AS candidate_id, shared AS shared_skills, cnt AS shared_count "
                "ORDER BY cnt DESC LIMIT 10",
                cid=candidate_id, min_shared=min_shared_skills,
            )
            return [dict(r) for r in result]

    # --- Fallback (no Neo4j) ---

    def _fallback_related_skills(self, skill: str) -> list[dict]:
        """Rule-based skill relationships when Neo4j unavailable."""
        SKILL_GRAPH = {
            "python": ["fastapi", "django", "flask", "numpy", "pandas", "machine learning"],
            "javascript": ["react", "node.js", "typescript", "angular", "vue"],
            "react": ["javascript", "typescript", "redux", "next.js"],
            "machine learning": ["python", "tensorflow", "pytorch", "deep learning", "nlp"],
            "aws": ["docker", "kubernetes", "terraform", "cloud", "devops"],
            "docker": ["kubernetes", "devops", "ci/cd", "microservices"],
            "fastapi": ["python", "rest", "postgresql", "docker"],
            "postgresql": ["sql", "database", "sqlalchemy", "python"],
            "data science": ["python", "machine learning", "statistics", "pandas", "numpy"],
            "devops": ["docker", "kubernetes", "ci/cd", "aws", "terraform", "linux"],
            "nlp": ["python", "machine learning", "deep learning", "transformers", "spacy"],
            "deep learning": ["tensorflow", "pytorch", "machine learning", "python"],
        }

        related = SKILL_GRAPH.get(skill.lower(), [])
        results = [{"name": s, "category": "general", "distance": 1} for s in related]

        # Second level
        for s in related[:3]:
            for s2 in SKILL_GRAPH.get(s, [])[:2]:
                if s2 != skill.lower() and s2 not in related:
                    results.append({"name": s2, "category": "general", "distance": 2})

        return results[:20]

    def get_skill_graph_summary(self) -> dict:
        """Get summary of the knowledge graph."""
        if not self.is_available:
            return {
                "status": "using_fallback",
                "message": "Neo4j not configured. Using rule-based skill relationships.",
                "fallback_skills_count": 12,
            }

        with self.driver.session() as session:
            skills = session.run("MATCH (s:Skill) RETURN count(s) AS count").single()
            candidates = session.run("MATCH (c:Candidate) RETURN count(c) AS count").single()
            relationships = session.run("MATCH ()-[r]->() RETURN count(r) AS count").single()

            return {
                "status": "connected",
                "skills_count": skills["count"],
                "candidates_count": candidates["count"],
                "relationships_count": relationships["count"],
            }


# Singleton
knowledge_graph = KnowledgeGraphService()
