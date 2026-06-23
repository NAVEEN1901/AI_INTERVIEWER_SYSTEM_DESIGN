"""AI Interview Question Generation Service.

Uses prompt engineering with context augmentation to generate
personalized interview questions based on:
- Job requirements
- Candidate skills and experience
- Difficulty level
"""

import random
from typing import Optional

from app.services.llm_service import llm_service


# --- Prompt Templates ---

SYSTEM_PROMPT_QUESTIONS = """You are an expert technical interviewer for a recruitment platform.
Generate interview questions that are:
- Relevant to the job requirements and candidate's background
- Progressively challenging (easy → medium → hard)
- A mix of technical, behavioral, and situational questions
- Clear and unambiguous
- Designed to assess real competency, not just memorization

Always return valid JSON."""

USER_PROMPT_TEMPLATE = """Generate {num_questions} interview questions for this candidate and job.

**Job Title:** {job_title}
**Job Description:** {job_description}
**Required Skills:** {required_skills}
**Preferred Skills:** {preferred_skills}
**Experience Required:** {min_experience}-{max_experience} years

**Candidate Profile:**
- Skills: {candidate_skills}
- Experience: {candidate_experience} years
- Education: {candidate_education}

**Difficulty Level:** {difficulty}

Return JSON format:
{{
    "questions": [
        {{
            "id": 1,
            "question": "...",
            "category": "technical|behavioral|situational|problem_solving",
            "difficulty": "easy|medium|hard",
            "skill_assessed": "...",
            "expected_answer_points": ["key point 1", "key point 2", ...]
        }}
    ]
}}"""


# --- Fallback Question Bank (when LLM not available) ---

QUESTION_BANK = {
    "technical": {
        "easy": [
            {"q": "Explain the difference between {skill} and its alternatives. When would you choose {skill}?", "category": "technical"},
            {"q": "What are the key features of {skill} that you use most frequently?", "category": "technical"},
            {"q": "Describe how you would set up a new project using {skill}.", "category": "technical"},
        ],
        "medium": [
            {"q": "How would you optimize a {skill} application for performance?", "category": "technical"},
            {"q": "Describe a challenging bug you encountered with {skill} and how you resolved it.", "category": "technical"},
            {"q": "What design patterns do you commonly use with {skill}?", "category": "technical"},
            {"q": "How do you handle error handling and testing in {skill}?", "category": "technical"},
        ],
        "hard": [
            {"q": "Design a scalable system using {skill} that handles millions of requests. Walk me through your architecture.", "category": "technical"},
            {"q": "What are the limitations of {skill} and how would you work around them in a production environment?", "category": "technical"},
            {"q": "How would you implement a distributed system using {skill} with fault tolerance?", "category": "technical"},
        ],
    },
    "behavioral": [
        {"q": "Tell me about a time you disagreed with a team decision. How did you handle it?", "category": "behavioral"},
        {"q": "Describe a project where you had to learn a new technology quickly. What was your approach?", "category": "behavioral"},
        {"q": "Give an example of how you've mentored a junior developer.", "category": "behavioral"},
        {"q": "Tell me about a time you failed. What did you learn from it?", "category": "behavioral"},
        {"q": "How do you prioritize tasks when you have multiple deadlines?", "category": "behavioral"},
    ],
    "situational": [
        {"q": "If you discovered a critical security vulnerability in production, what steps would you take?", "category": "situational"},
        {"q": "How would you approach migrating a legacy system to a modern architecture?", "category": "situational"},
        {"q": "If your team was behind schedule on a sprint, what would you do?", "category": "situational"},
    ],
}


def generate_questions_with_llm(
    job_title: str,
    job_description: str,
    required_skills: list[str],
    preferred_skills: list[str],
    min_experience: float,
    max_experience: Optional[float],
    candidate_skills: list[str],
    candidate_experience: float,
    candidate_education: list[dict],
    num_questions: int = 8,
    difficulty: str = "mixed",
) -> dict:
    """Generate interview questions using LLM with prompt engineering."""
    user_prompt = USER_PROMPT_TEMPLATE.format(
        num_questions=num_questions,
        job_title=job_title,
        job_description=job_description[:1000],
        required_skills=", ".join(required_skills),
        preferred_skills=", ".join(preferred_skills),
        min_experience=min_experience,
        max_experience=max_experience or "any",
        candidate_skills=", ".join(candidate_skills[:15]),
        candidate_experience=candidate_experience,
        candidate_education=str(candidate_education[:3]),
        difficulty=difficulty,
    )

    result = llm_service.generate_json(
        system_prompt=SYSTEM_PROMPT_QUESTIONS,
        user_prompt=user_prompt,
        temperature=0.7,
    )

    if result and "questions" in result:
        return result
    return None


def generate_questions_fallback(
    required_skills: list[str],
    candidate_skills: list[str],
    num_questions: int = 8,
    difficulty: str = "mixed",
) -> dict:
    """Generate questions using rule-based fallback (no LLM needed)."""
    questions = []
    question_id = 1

    # Determine skills to ask about (intersection of required and candidate skills)
    common_skills = list(set(s.lower() for s in required_skills) & set(s.lower() for s in candidate_skills))
    if not common_skills:
        common_skills = required_skills[:5] if required_skills else candidate_skills[:5]

    # Distribute questions across categories and difficulties
    if difficulty == "mixed":
        difficulties = ["easy"] * 2 + ["medium"] * 4 + ["hard"] * 2
    elif difficulty == "easy":
        difficulties = ["easy"] * num_questions
    elif difficulty == "hard":
        difficulties = ["hard"] * num_questions
    else:
        difficulties = ["medium"] * num_questions

    random.shuffle(difficulties)

    # Technical questions
    tech_count = int(num_questions * 0.5)
    for i in range(min(tech_count, len(difficulties))):
        diff = difficulties[i]
        skill = random.choice(common_skills) if common_skills else "the technology"
        templates = QUESTION_BANK["technical"].get(diff, QUESTION_BANK["technical"]["medium"])
        template = random.choice(templates)
        questions.append({
            "id": question_id,
            "question": template["q"].format(skill=skill),
            "category": "technical",
            "difficulty": diff,
            "skill_assessed": skill,
            "expected_answer_points": [],
        })
        question_id += 1

    # Behavioral questions
    behavioral_count = int(num_questions * 0.3)
    behavioral_pool = random.sample(
        QUESTION_BANK["behavioral"],
        min(behavioral_count, len(QUESTION_BANK["behavioral"])),
    )
    for q in behavioral_pool:
        questions.append({
            "id": question_id,
            "question": q["q"],
            "category": "behavioral",
            "difficulty": "medium",
            "skill_assessed": "soft_skills",
            "expected_answer_points": [],
        })
        question_id += 1

    # Situational questions
    remaining = num_questions - len(questions)
    situational_pool = random.sample(
        QUESTION_BANK["situational"],
        min(remaining, len(QUESTION_BANK["situational"])),
    )
    for q in situational_pool:
        questions.append({
            "id": question_id,
            "question": q["q"],
            "category": "situational",
            "difficulty": "medium",
            "skill_assessed": "problem_solving",
            "expected_answer_points": [],
        })
        question_id += 1

    return {"questions": questions[:num_questions]}


def generate_interview_questions(
    job_title: str,
    job_description: str,
    required_skills: list[str],
    preferred_skills: list[str],
    min_experience: float = 0,
    max_experience: Optional[float] = None,
    candidate_skills: list[str] = None,
    candidate_experience: float = 0,
    candidate_education: list[dict] = None,
    num_questions: int = 8,
    difficulty: str = "mixed",
) -> dict:
    """
    Generate personalized interview questions.
    Uses LLM if available, falls back to rule-based generation.
    """
    candidate_skills = candidate_skills or []
    candidate_education = candidate_education or []

    # Try LLM first
    if llm_service.is_available:
        result = generate_questions_with_llm(
            job_title=job_title,
            job_description=job_description,
            required_skills=required_skills,
            preferred_skills=preferred_skills,
            min_experience=min_experience,
            max_experience=max_experience,
            candidate_skills=candidate_skills,
            candidate_experience=candidate_experience,
            candidate_education=candidate_education,
            num_questions=num_questions,
            difficulty=difficulty,
        )
        if result:
            return result

    # Fallback to rule-based
    return generate_questions_fallback(
        required_skills=required_skills,
        candidate_skills=candidate_skills,
        num_questions=num_questions,
        difficulty=difficulty,
    )
