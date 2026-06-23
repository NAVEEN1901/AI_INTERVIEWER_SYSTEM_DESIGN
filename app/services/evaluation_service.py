"""AI Evaluation Service - evaluates candidate responses with explainable scoring.

Implements:
- Response evaluation against expected answers
- Hallucination detection / faithfulness scoring
- Explainable AI recommendations
- Multi-dimensional scoring (technical, communication, problem-solving)
"""

import re
from typing import Optional

from app.services.llm_service import llm_service
from app.services.embedding_service import generate_embedding, cosine_similarity


# --- Prompt Templates ---

SYSTEM_PROMPT_EVALUATE = """You are an expert interview evaluator for a technical recruitment platform.
Evaluate candidate responses objectively and provide:
- Scores based on depth, accuracy, and relevance
- Specific strengths and weaknesses
- Clear explanations for your scoring
- Actionable feedback

Be fair but rigorous. Consider partial credit for partially correct answers.
Always return valid JSON."""

USER_PROMPT_EVALUATE = """Evaluate this candidate's interview responses.

**Job Title:** {job_title}
**Required Skills:** {required_skills}

**Questions and Responses:**
{qa_pairs}

Return JSON format:
{{
    "overall_score": 0-100,
    "technical_score": 0-100,
    "communication_score": 0-100,
    "problem_solving_score": 0-100,
    "question_evaluations": [
        {{
            "question_id": 1,
            "score": 0-100,
            "strengths": ["..."],
            "weaknesses": ["..."],
            "feedback": "..."
        }}
    ],
    "overall_strengths": ["..."],
    "overall_weaknesses": ["..."],
    "recommendation": "hire|maybe|reject",
    "explanation": "Detailed justification for the recommendation",
    "faithfulness_score": 0-100
}}"""


# --- Evaluation Metrics ---

def evaluate_response_similarity(response: str, expected_points: list[str]) -> float:
    """Evaluate response against expected answer points using semantic similarity."""
    if not expected_points or not response:
        return 50.0  # Neutral score if no expected points

    response_embedding = generate_embedding(response)
    scores = []

    for point in expected_points:
        point_embedding = generate_embedding(point)
        similarity = cosine_similarity(response_embedding, point_embedding)
        scores.append(similarity)

    # Average similarity * 100
    return round((sum(scores) / len(scores)) * 100, 2) if scores else 50.0


def evaluate_response_length(response: str, min_words: int = 20, ideal_words: int = 100) -> float:
    """Score based on response length (too short = low score)."""
    word_count = len(response.split())
    if word_count < min_words:
        return max(20, (word_count / min_words) * 60)
    elif word_count <= ideal_words * 2:
        return 100.0
    else:
        # Slight penalty for overly verbose answers
        return max(70, 100 - (word_count - ideal_words * 2) * 0.1)


def detect_hallucination_indicators(response: str) -> dict:
    """
    Simple hallucination/faithfulness check.
    Looks for overconfident claims, contradictions, or vague filler.
    """
    indicators = {
        "vague_fillers": 0,
        "overconfident_claims": 0,
        "specific_details": 0,
    }

    # Vague filler phrases
    vague_patterns = [
        r"\b(basically|essentially|sort of|kind of|you know|like)\b",
        r"\b(i think maybe|perhaps|not sure but)\b",
    ]
    for pattern in vague_patterns:
        indicators["vague_fillers"] += len(re.findall(pattern, response.lower()))

    # Overconfident claims without evidence
    overconfident_patterns = [
        r"\b(always|never|every|all)\b",
        r"\b(best in the world|revolutionary|unprecedented)\b",
    ]
    for pattern in overconfident_patterns:
        indicators["overconfident_claims"] += len(re.findall(pattern, response.lower()))

    # Specific details (positive indicator)
    specific_patterns = [
        r"\b\d+%?\b",  # Numbers
        r"\b(for example|specifically|in my experience at)\b",
        r"\b(implemented|built|designed|deployed|achieved)\b",
    ]
    for pattern in specific_patterns:
        indicators["specific_details"] += len(re.findall(pattern, response.lower()))

    # Faithfulness score: more specifics = higher, more vagueness = lower
    faithfulness = 70  # Base score
    faithfulness += min(20, indicators["specific_details"] * 5)
    faithfulness -= min(30, indicators["vague_fillers"] * 5)
    faithfulness -= min(15, indicators["overconfident_claims"] * 5)

    return {
        "faithfulness_score": max(0, min(100, faithfulness)),
        "indicators": indicators,
    }


def evaluate_with_llm(
    job_title: str,
    required_skills: list[str],
    questions_and_responses: list[dict],
) -> Optional[dict]:
    """Evaluate responses using LLM."""
    if not llm_service.is_available:
        return None

    # Format Q&A pairs
    qa_text = ""
    for i, qa in enumerate(questions_and_responses, 1):
        qa_text += f"\nQ{i}: {qa['question']}\n"
        qa_text += f"A{i}: {qa['response']}\n"
        if qa.get("expected_answer_points"):
            qa_text += f"Expected points: {', '.join(qa['expected_answer_points'])}\n"

    user_prompt = USER_PROMPT_EVALUATE.format(
        job_title=job_title,
        required_skills=", ".join(required_skills),
        qa_pairs=qa_text,
    )

    result = llm_service.generate_json(
        system_prompt=SYSTEM_PROMPT_EVALUATE,
        user_prompt=user_prompt,
        temperature=0.3,
    )

    return result if result and "overall_score" in result else None


def evaluate_responses_fallback(
    questions_and_responses: list[dict],
) -> dict:
    """Rule-based evaluation when LLM is not available."""
    question_evaluations = []
    total_score = 0
    technical_scores = []
    communication_scores = []

    for qa in questions_and_responses:
        response = qa.get("response", "")
        expected_points = qa.get("expected_answer_points", [])
        category = qa.get("category", "technical")

        # Semantic similarity score
        similarity_score = evaluate_response_similarity(response, expected_points)

        # Length score
        length_score = evaluate_response_length(response)

        # Faithfulness check
        faithfulness = detect_hallucination_indicators(response)

        # Combined question score
        question_score = (
            similarity_score * 0.4
            + length_score * 0.2
            + faithfulness["faithfulness_score"] * 0.4
        )

        # Track category scores
        if category == "technical":
            technical_scores.append(question_score)
        else:
            communication_scores.append(question_score)

        strengths = []
        weaknesses = []

        if similarity_score > 70:
            strengths.append("Covers key expected points")
        elif similarity_score < 40:
            weaknesses.append("Missing key expected points")

        if length_score > 80:
            strengths.append("Well-structured response with adequate detail")
        elif length_score < 50:
            weaknesses.append("Response is too brief")

        if faithfulness["faithfulness_score"] > 75:
            strengths.append("Specific and grounded in experience")
        elif faithfulness["faithfulness_score"] < 50:
            weaknesses.append("Response lacks specific details or examples")

        question_evaluations.append({
            "question_id": qa.get("id", 0),
            "score": round(question_score, 2),
            "strengths": strengths,
            "weaknesses": weaknesses,
            "feedback": f"Score breakdown: relevance={similarity_score:.0f}, depth={length_score:.0f}, faithfulness={faithfulness['faithfulness_score']:.0f}",
        })

        total_score += question_score

    # Calculate averages
    num_questions = len(questions_and_responses) or 1
    overall_score = round(total_score / num_questions, 2)
    technical_score = round(sum(technical_scores) / len(technical_scores), 2) if technical_scores else 0
    communication_score = round(sum(communication_scores) / len(communication_scores), 2) if communication_scores else overall_score

    # Determine recommendation
    if overall_score >= 70:
        recommendation = "hire"
        explanation = f"Strong overall performance ({overall_score}/100). Candidate demonstrates solid technical knowledge and communication skills."
    elif overall_score >= 50:
        recommendation = "maybe"
        explanation = f"Average performance ({overall_score}/100). Some areas show potential but others need improvement. Consider follow-up interview."
    else:
        recommendation = "reject"
        explanation = f"Below expectations ({overall_score}/100). Candidate's responses lack depth and specificity for the role requirements."

    # Collect overall strengths/weaknesses
    all_strengths = list(set(s for qe in question_evaluations for s in qe["strengths"]))
    all_weaknesses = list(set(w for qe in question_evaluations for w in qe["weaknesses"]))

    return {
        "overall_score": overall_score,
        "technical_score": technical_score,
        "communication_score": communication_score,
        "problem_solving_score": round((technical_score + communication_score) / 2, 2),
        "question_evaluations": question_evaluations,
        "overall_strengths": all_strengths[:5],
        "overall_weaknesses": all_weaknesses[:5],
        "recommendation": recommendation,
        "explanation": explanation,
        "faithfulness_score": round(
            sum(detect_hallucination_indicators(qa.get("response", ""))["faithfulness_score"]
                for qa in questions_and_responses) / num_questions, 2
        ),
    }


def evaluate_interview(
    job_title: str,
    required_skills: list[str],
    questions_and_responses: list[dict],
) -> dict:
    """
    Evaluate interview responses.
    Uses LLM if available, falls back to rule-based evaluation.
    
    Args:
        job_title: The job title being interviewed for
        required_skills: List of required skills for the job
        questions_and_responses: List of dicts with keys:
            - id, question, response, category, expected_answer_points
    
    Returns:
        Comprehensive evaluation with scores, strengths, weaknesses, and recommendation
    """
    # Try LLM first
    if llm_service.is_available:
        result = evaluate_with_llm(job_title, required_skills, questions_and_responses)
        if result:
            return result

    # Fallback to rule-based
    return evaluate_responses_fallback(questions_and_responses)
