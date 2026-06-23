# AI Talent Acquisition Platform

Enterprise AI-powered recruitment platform built with FastAPI, PostgreSQL, and modern AI/ML stack.

## Architecture

```
Frontend (React) → FastAPI APIs → PostgreSQL
                                → Resume Processing (NLP)
                                → Hybrid Search (BM25 + Vector)
                                → Qdrant/Pinecone (Vector DB)
                                → LLM (Prompt Engineering)
                                → Neo4j (Graph RAG)
                                → Whisper (Voice Interview)
                                → Azure ML + Monitoring
                                → Docker + CI/CD
```

## Quick Start

### 1. Setup Environment
```bash
cd ai-talent-platform
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac
pip install -r requirements.txt
```

### 2. Configure Environment
```bash
copy .env.example .env
# Edit .env with your database credentials
```

### 3. Run Database Migrations
```bash
alembic upgrade head
```

### 4. Start Server
```bash
uvicorn app.main:app --reload --port 8000
```

### 5. API Docs
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Project Structure

```
ai-talent-platform/
├── app/
│   ├── main.py              # FastAPI application entry
│   ├── core/
│   │   ├── config.py        # Settings & environment
│   │   ├── security.py      # JWT, password hashing
│   │   └── dependencies.py  # Dependency injection
│   ├── api/v1/
│   │   ├── router.py        # API router aggregator
│   │   └── endpoints/
│   │       ├── auth.py       # Login, register, logout
│   │       ├── users.py      # User management
│   │       ├── jobs.py       # Job description CRUD
│   │       ├── resumes.py    # Resume upload & parsing
│   │       ├── interviews.py # Interview management
│   │       └── evaluations.py# AI evaluations
│   ├── models/               # SQLAlchemy ORM models
│   ├── schemas/              # Pydantic schemas
│   ├── services/             # Business logic
│   ├── db/
│   │   ├── session.py        # Database session
│   │   └── base.py           # Base model
│   └── utils/                # Utilities
├── alembic/                  # Database migrations
├── tests/                    # Test suite
├── uploads/resumes/          # Resume file storage
├── requirements.txt
├── .env.example
├── Dockerfile
└── docker-compose.yml
```

## Sprint Roadmap

| Sprint | Goal | Points |
|--------|------|--------|
| 1 | Auth + DB + APIs | 26 |
| 2 | Resume Intelligence | 26 |
| 3 | Semantic Search & Ranking | 34 |
| 4 | GenAI Evaluation | 26 |
| 5 | Voice + Graph RAG | 42 |
| 6 | MLOps & Deployment | 60 |

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Backend | FastAPI |
| Database | PostgreSQL |
| Vector DB | Qdrant / Pinecone |
| ORM | SQLAlchemy |
| Migrations | Alembic |
| Auth | JWT + bcrypt |
| ML Platform | Azure ML |
| Speech-to-Text | Whisper |
| Graph DB | Neo4j |
| Deployment | Docker + GitHub Actions |
