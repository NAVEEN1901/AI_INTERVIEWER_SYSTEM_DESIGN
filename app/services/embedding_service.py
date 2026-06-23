"""Vector Embedding Service - generates and manages embeddings for semantic search."""

from typing import Optional
import numpy as np

# Lazy loading to avoid slow startup
_model = None


def get_embedding_model():
    """Lazy-load the sentence transformer model."""
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer("all-MiniLM-L6-v2")
    return _model


def generate_embedding(text: str) -> list[float]:
    """Generate embedding vector for a text string."""
    model = get_embedding_model()
    embedding = model.encode(text, normalize_embeddings=True)
    return embedding.tolist()


def generate_embeddings_batch(texts: list[str], batch_size: int = 32) -> list[list[float]]:
    """Generate embeddings for multiple texts efficiently."""
    model = get_embedding_model()
    embeddings = model.encode(texts, normalize_embeddings=True, batch_size=batch_size)
    return embeddings.tolist()


def cosine_similarity(vec1: list[float], vec2: list[float]) -> float:
    """Calculate cosine similarity between two vectors."""
    a = np.array(vec1)
    b = np.array(vec2)
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-10))


def prepare_resume_text_for_embedding(
    skills: list[str],
    experience_years: float,
    raw_text: str,
    max_length: int = 512,
) -> str:
    """
    Prepare resume text for embedding generation.
    Prioritizes skills and key info for better semantic matching.
    """
    # Build structured summary for better embeddings
    parts = []
    if skills:
        parts.append(f"Skills: {', '.join(skills)}")
    if experience_years > 0:
        parts.append(f"Experience: {experience_years} years")

    # Add beginning of raw text (usually summary/headline)
    structured = " | ".join(parts)
    remaining_chars = max_length * 4 - len(structured)  # Rough char-to-token estimate
    if remaining_chars > 100:
        parts.append(raw_text[:remaining_chars])

    return " | ".join(parts)


def prepare_job_text_for_embedding(
    title: str,
    description: str,
    required_skills: list[str],
    preferred_skills: list[str],
    max_length: int = 512,
) -> str:
    """Prepare job description text for embedding generation."""
    parts = [f"Job: {title}"]
    if required_skills:
        parts.append(f"Required Skills: {', '.join(required_skills)}")
    if preferred_skills:
        parts.append(f"Preferred Skills: {', '.join(preferred_skills)}")
    parts.append(description[:1000])
    return " | ".join(parts)
