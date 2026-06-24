"""JD Matching service - matches resumes against job descriptions using BM25 + keyword matching."""

import re
import math
from collections import Counter
from typing import Optional

import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
from nltk.stem import WordNetLemmatizer
from rank_bm25 import BM25Okapi

# Download NLTK data (one-time)
try:
    nltk.data.find("tokenizers/punkt_tab")
except LookupError:
    nltk.download("punkt_tab", quiet=True)
try:
    nltk.data.find("corpora/stopwords")
except LookupError:
    nltk.download("stopwords", quiet=True)
try:
    nltk.data.find("corpora/wordnet")
except LookupError:
    nltk.download("wordnet", quiet=True)

# Initialize
stop_words = set(stopwords.words("english"))
lemmatizer = WordNetLemmatizer()


def preprocess_text(text: str) -> list[str]:
    """Tokenize, lowercase, remove stopwords, and lemmatize."""
    # Lowercase and remove special characters
    text = re.sub(r"[^a-zA-Z0-9\s\.\+\#]", " ", text.lower())
    # Tokenize
    tokens = word_tokenize(text)
    # Remove stopwords and lemmatize
    processed = [
        lemmatizer.lemmatize(token)
        for token in tokens
        if token not in stop_words and len(token) > 1
    ]
    return processed


def extract_keywords(text: str, top_n: int = 30) -> list[str]:
    """Extract top keywords from text using TF-based ranking."""
    tokens = preprocess_text(text)
    freq = Counter(tokens)
    return [word for word, _ in freq.most_common(top_n)]


def calculate_skill_match_score(
    candidate_skills: list[str],
    required_skills: list[str],
    preferred_skills: list[str] = None,
) -> dict:
    """
    Calculate skill match score between candidate and job requirements.
    
    Returns:
        dict with score (0-100), matched_required, matched_preferred, missing_required
    """
    if not required_skills:
        return {"score": 0, "matched_required": [], "matched_preferred": [], "missing_required": []}

    candidate_skills_lower = {s.lower() for s in candidate_skills}
    required_lower = {s.lower() for s in required_skills}
    preferred_lower = {s.lower() for s in (preferred_skills or [])}

    matched_required = candidate_skills_lower & required_lower
    matched_preferred = candidate_skills_lower & preferred_lower
    missing_required = required_lower - candidate_skills_lower

    # Score: 70% weight on required skills, 30% on preferred
    required_score = (len(matched_required) / len(required_lower)) * 70 if required_lower else 0
    preferred_score = (
        (len(matched_preferred) / len(preferred_lower)) * 30
        if preferred_lower
        else 30  # Full marks if no preferred skills defined
    )

    total_score = min(100, required_score + preferred_score)

    return {
        "score": round(total_score, 2),
        "matched_required": sorted(matched_required),
        "matched_preferred": sorted(matched_preferred),
        "missing_required": sorted(missing_required),
    }


def calculate_experience_match(
    candidate_years: float,
    min_years: float,
    max_years: Optional[float] = None,
) -> dict:
    """Score experience match."""
    if candidate_years >= min_years:
        if max_years and candidate_years > max_years:
            # Overqualified penalty (mild)
            score = max(70, 100 - (candidate_years - max_years) * 5)
        else:
            score = 100.0
    else:
        # Under-qualified
        score = max(0, (candidate_years / min_years) * 100) if min_years > 0 else 100

    return {
        "score": round(score, 2),
        "candidate_years": candidate_years,
        "required_min": min_years,
        "required_max": max_years,
    }


class JDMatcher:
    """Job Description matching engine using BM25 + skill matching."""

    def __init__(self):
        self.bm25: Optional[BM25Okapi] = None
        self.corpus_tokens: list[list[str]] = []
        self.candidate_ids: list[int] = []

    def build_index(self, documents: list[dict]):
        """
        Build BM25 index from candidate documents.
        
        Args:
            documents: list of {"candidate_id": int, "text": str}
        """
        self.corpus_tokens = []
        self.candidate_ids = []

        for doc in documents:
            tokens = preprocess_text(doc["text"])
            self.corpus_tokens.append(tokens)
            self.candidate_ids.append(doc["candidate_id"])

        if self.corpus_tokens:
            self.bm25 = BM25Okapi(self.corpus_tokens)

    def search(self, query: str, top_k: int = 10) -> list[dict]:
        """
        Search candidates using BM25 ranking.
        
        Returns:
            list of {"candidate_id": int, "bm25_score": float, "rank": int}
        """
        if not self.bm25:
            return []

        query_tokens = preprocess_text(query)
        scores = self.bm25.get_scores(query_tokens)

        # Rank by score
        ranked = sorted(
            zip(self.candidate_ids, scores),
            key=lambda x: x[1],
            reverse=True,
        )[:top_k]

        # Normalize scores to 0-100
        max_score = ranked[0][1] if ranked and ranked[0][1] > 0 else 1
        return [
            {
                "candidate_id": cid,
                "bm25_score": round((score / max_score) * 100, 2),
                "rank": idx + 1,
            }
            for idx, (cid, score) in enumerate(ranked)
            if score > 0
        ]

    def match_candidate_to_job(
        self,
        candidate_skills: list[str],
        candidate_experience: float,
        candidate_text: str,
        job_required_skills: list[str],
        job_preferred_skills: list[str],
        job_description: str,
        job_min_experience: float = 0,
        job_max_experience: Optional[float] = None,
    ) -> dict:
        """
        Comprehensive match scoring between a candidate and a job.
        
        Combines:
        - Skill match (40% weight)
        - BM25 text relevance (35% weight)
        - Experience match (25% weight)
        """
        # Skill matching
        skill_result = calculate_skill_match_score(
            candidate_skills, job_required_skills, job_preferred_skills
        )

        # Experience matching
        exp_result = calculate_experience_match(
            candidate_experience, job_min_experience, job_max_experience
        )

        # BM25 text relevance (single document)
        candidate_tokens = preprocess_text(candidate_text)
        job_tokens = preprocess_text(job_description)
        if candidate_tokens:
            bm25_single = BM25Okapi([candidate_tokens])
            bm25_scores = bm25_single.get_scores(job_tokens)
            text_score = min(100, bm25_scores[0] * 10) if bm25_scores[0] > 0 else 0
        else:
            text_score = 0

        # Weighted composite score
        composite_score = (
            skill_result["score"] * 0.40
            + text_score * 0.35
            + exp_result["score"] * 0.25
        )

        return {
            "composite_score": round(composite_score, 2),
            "skill_match": skill_result,
            "experience_match": exp_result,
            "text_relevance_score": round(text_score, 2),
            "recommendation": _get_recommendation(composite_score),
        }


def _get_recommendation(score: float) -> str:
    """Generate recommendation based on composite score."""
    if score >= 75:
        return "strongly_recommended"
    elif score >= 55:
        return "recommended"
    elif score >= 35:
        return "potential_fit"
    else:
        return "not_recommended"


# Singleton matcher instance
jd_matcher = JDMatcher()
