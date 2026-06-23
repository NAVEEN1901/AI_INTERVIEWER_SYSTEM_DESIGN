"""Create sample resume files for testing."""

import os

SAMPLE_RESUMES = [
    {
        "filename": "john_doe_resume.txt",
        "content": """JOHN DOE
Software Engineer | john.doe@email.com | +1-555-0101 | San Francisco, CA
LinkedIn: linkedin.com/in/johndoe | GitHub: github.com/johndoe

SUMMARY
Experienced software engineer with 6+ years of experience in Python, cloud computing, 
and building scalable microservices. Passionate about AI/ML and DevOps practices.

SKILLS
Python, FastAPI, Django, JavaScript, React, Node.js, Docker, Kubernetes, AWS, 
PostgreSQL, MongoDB, Redis, Kafka, Machine Learning, TensorFlow, CI/CD, Git

EXPERIENCE
Senior Software Engineer | TechCorp Inc. | 2021 - Present
- Designed and built microservices using FastAPI serving 10M+ requests/day
- Implemented ML pipeline for recommendation engine using TensorFlow
- Led migration from monolith to Kubernetes-based microservices on AWS
- Mentored team of 4 junior developers

Software Engineer | DataFlow Systems | 2018 - 2021
- Built real-time data pipelines using Apache Kafka and Python
- Developed REST APIs with Django handling 5M daily requests
- Implemented CI/CD pipelines using GitHub Actions and Docker
- Reduced infrastructure costs by 40% through optimization

EDUCATION
M.S. in Computer Science | Stanford University | 2018
B.Tech in Information Technology | IIT Bombay | 2016

CERTIFICATIONS
- AWS Solutions Architect Professional
- Certified Kubernetes Administrator (CKA)
""",
    },
    {
        "filename": "jane_smith_resume.txt",
        "content": """JANE SMITH
Data Scientist | jane.smith@email.com | +1-555-0202 | New York, NY

PROFESSIONAL SUMMARY
Data scientist with 4 years of experience specializing in NLP, deep learning,
and MLOps. Strong background in statistical modeling and production ML systems.

TECHNICAL SKILLS
Python, R, SQL, TensorFlow, PyTorch, Scikit-learn, Pandas, NumPy, Spark,
NLP, Computer Vision, AWS SageMaker, Docker, MLflow, Airflow, Tableau, Power BI

WORK EXPERIENCE
Senior Data Scientist | AI Solutions Corp | 2022 - Present
- Built NLP-based resume screening system using BERT and spaCy
- Deployed ML models on AWS SageMaker with automated retraining
- Created real-time analytics dashboard using Tableau
- Improved model accuracy by 25% using ensemble techniques

Data Scientist | FinTech Analytics | 2020 - 2022
- Developed fraud detection models using Random Forest and XGBoost
- Built automated reporting pipeline using Python and Airflow
- Conducted A/B testing for product features
- Reduced false positive rate by 35%

EDUCATION
M.S. in Data Science | Columbia University | 2020
B.S. in Mathematics | UC Berkeley | 2018

PUBLICATIONS
- "Efficient NER for Resume Parsing" - ACL Workshop 2023
""",
    },
    {
        "filename": "alex_kumar_resume.txt",
        "content": """ALEX KUMAR
Full Stack Developer | alex.kumar@email.com | +91-9876543210 | Bangalore, India
GitHub: github.com/alexkumar

ABOUT ME
Full stack developer with 3 years of experience building web applications.
Proficient in React, Node.js, and cloud technologies.

SKILLS
JavaScript, TypeScript, React, Angular, Vue, Node.js, Express, Python,
FastAPI, PostgreSQL, MongoDB, Redis, Docker, AWS, Azure, Git, Agile, Scrum

EXPERIENCE
Full Stack Developer | WebTech Solutions | 2022 - Present
- Built e-commerce platform using React + Node.js serving 50K users
- Implemented real-time notifications using WebSockets
- Migrated legacy PHP application to modern React/FastAPI stack
- Conducted code reviews and maintained CI/CD pipelines

Junior Developer | StartupXYZ | 2021 - 2022
- Developed REST APIs using Express.js and MongoDB
- Built responsive UI components using React and Material-UI
- Participated in Agile sprints with 2-week iterations

EDUCATION
B.Tech in Computer Science | NIT Trichy | 2021

PROJECTS
- Open source contribution to FastAPI documentation
- Personal blog built with Next.js (10K monthly visitors)
""",
    },
]


def create_sample_resumes():
    """Create sample resume files in uploads/resumes directory."""
    os.makedirs("uploads/resumes", exist_ok=True)
    for resume in SAMPLE_RESUMES:
        path = os.path.join("uploads/resumes", resume["filename"])
        with open(path, "w", encoding="utf-8") as f:
            f.write(resume["content"])
        print(f"Created: {path}")
    print(f"\n{len(SAMPLE_RESUMES)} sample resumes created.")


if __name__ == "__main__":
    create_sample_resumes()
