"""Resume parsing service - extracts structured data from resumes using NLP."""

import re
from pathlib import Path
from typing import Optional

import fitz  # PyMuPDF
import spacy
from docx import Document

# Load spaCy model
nlp = spacy.load("en_core_web_sm")

# Common skills list for extraction
TECH_SKILLS = {
    "python", "java", "javascript", "typescript", "c++", "c#", "go", "rust", "ruby",
    "php", "swift", "kotlin", "scala", "r", "matlab", "sql", "nosql", "html", "css",
    "react", "angular", "vue", "node.js", "express", "django", "flask", "fastapi",
    "spring", "docker", "kubernetes", "aws", "azure", "gcp", "terraform", "ansible",
    "jenkins", "github actions", "ci/cd", "git", "linux", "mongodb", "postgresql",
    "mysql", "redis", "elasticsearch", "kafka", "rabbitmq", "graphql", "rest",
    "machine learning", "deep learning", "nlp", "computer vision", "tensorflow",
    "pytorch", "scikit-learn", "pandas", "numpy", "spark", "hadoop", "airflow",
    "tableau", "power bi", "excel", "agile", "scrum", "jira", "figma", "photoshop",
    ".net", "unity", "unreal", "blockchain", "solidity", "microservices", "devops",
    "data engineering", "data science", "artificial intelligence", "ai", "ml",
}

# Education keywords
DEGREE_PATTERNS = [
    r"(?i)(b\.?s\.?|bachelor(?:'s)?)\s+(?:of\s+)?(?:science|arts|engineering|technology)",
    r"(?i)(m\.?s\.?|master(?:'s)?)\s+(?:of\s+)?(?:science|arts|engineering|technology|business)",
    r"(?i)(ph\.?d\.?|doctorate)",
    r"(?i)(mba|m\.b\.a\.)",
    r"(?i)(b\.?tech|b\.?e\.?)",
    r"(?i)(m\.?tech|m\.?e\.?)",
]


def extract_text_from_pdf(file_path: str) -> str:
    """Extract text from a PDF file."""
    doc = fitz.open(file_path)
    text = ""
    for page in doc:
        text += page.get_text()
    doc.close()
    return text


def extract_text_from_docx(file_path: str) -> str:
    """Extract text from a DOCX file."""
    doc = Document(file_path)
    return "\n".join([para.text for para in doc.paragraphs])


def extract_text_from_txt(file_path: str) -> str:
    """Extract text from a TXT file."""
    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        return f.read()


def extract_text(file_path: str) -> str:
    """Extract text from resume file based on extension."""
    ext = Path(file_path).suffix.lower()
    extractors = {
        ".pdf": extract_text_from_pdf,
        ".docx": extract_text_from_docx,
        ".txt": extract_text_from_txt,
    }
    extractor = extractors.get(ext)
    if not extractor:
        raise ValueError(f"Unsupported file type: {ext}")
    return extractor(file_path)


def extract_email(text: str) -> Optional[str]:
    """Extract email address from text."""
    pattern = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
    match = re.search(pattern, text)
    return match.group(0) if match else None


def extract_phone(text: str) -> Optional[str]:
    """Extract phone number from text."""
    pattern = r"[\+]?[(]?[0-9]{1,4}[)]?[-\s\./0-9]{7,15}"
    match = re.search(pattern, text)
    return match.group(0).strip() if match else None


def extract_name(doc) -> Optional[str]:
    """Extract person name using NER."""
    for ent in doc.ents:
        if ent.label_ == "PERSON":
            return ent.text
    return None


def extract_skills(text: str) -> list[str]:
    """Extract technical skills from text."""
    text_lower = text.lower()
    found_skills = []
    for skill in TECH_SKILLS:
        # Use word boundary check for short skills
        if len(skill) <= 3:
            if re.search(rf"\b{re.escape(skill)}\b", text_lower):
                found_skills.append(skill)
        elif skill in text_lower:
            found_skills.append(skill)
    return sorted(set(found_skills))


def extract_experience_years(text: str) -> float:
    """Estimate years of experience from text."""
    patterns = [
        r"(\d+)\+?\s*(?:years?|yrs?)(?:\s+of)?\s+(?:experience|exp)",
        r"(?:experience|exp)(?:\s*:?\s*)(\d+)\+?\s*(?:years?|yrs?)",
        r"(\d+)\+?\s*(?:years?|yrs?)\s+(?:in|of|working)",
    ]
    max_years = 0.0
    for pattern in patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for match in matches:
            years = float(match)
            if years < 50:  # sanity check
                max_years = max(max_years, years)
    return max_years


def extract_education(text: str) -> list[dict]:
    """Extract education information."""
    education = []
    for pattern in DEGREE_PATTERNS:
        matches = re.finditer(pattern, text)
        for match in matches:
            # Get surrounding context for institution
            start = max(0, match.start() - 10)
            end = min(len(text), match.end() + 100)
            context = text[start:end]
            education.append({
                "degree": match.group(0).strip(),
                "context": context.strip()[:150],
            })
    return education


def parse_resume(file_path: str) -> dict:
    """
    Parse a resume file and extract structured data.
    
    Returns dict with: name, email, phone, skills, experience_years, education, raw_text
    """
    raw_text = extract_text(file_path)
    doc = nlp(raw_text[:100000])  # Limit for performance

    result = {
        "name": extract_name(doc),
        "email": extract_email(raw_text),
        "phone": extract_phone(raw_text),
        "skills": extract_skills(raw_text),
        "experience_years": extract_experience_years(raw_text),
        "education": extract_education(raw_text),
        "raw_text": raw_text,
        "word_count": len(raw_text.split()),
    }
    return result
