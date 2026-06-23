# AI Talent Acquisition Platform — Full Project Documentation

---

## 1. Project Overview

**AI Talent Acquisition Platform** is an enterprise-grade recruitment automation system that uses Artificial Intelligence to streamline candidate screening, interviewing, evaluation, and hiring decisions.

### Key Capabilities
- Automated resume parsing using NLP (Named Entity Recognition)
- Intelligent candidate-job matching using BM25 + Vector Search
- AI-powered interview question generation
- Voice interview support with Whisper speech-to-text
- Graph-based skill relationship analysis (Graph RAG)
- Explainable AI recommendations
- Real-time analytics dashboards
- Production-ready with Docker, CI/CD, and monitoring

---

## 2. Technology Stack

| Layer | Technology |
|-------|-----------|
| Backend Framework | FastAPI (Python) |
| Database | PostgreSQL + SQLAlchemy ORM |
| Migrations | Alembic |
| Authentication | JWT (python-jose) + bcrypt |
| Vector Database | Qdrant (in-memory for dev, server for prod) |
| Embeddings | sentence-transformers (all-MiniLM-L6-v2, 384-dim) |
| NLP | spaCy + NLTK |
| Lexical Search | BM25 (rank-bm25) |
| LLM | OpenAI / Azure OpenAI (GPT-4o-mini) |
| Speech-to-Text | OpenAI Whisper |
| Graph Database | Neo4j (with rule-based fallback) |
| Email | SMTP + Jinja2 templates |
| Containerization | Docker + docker-compose |
| CI/CD | GitHub Actions |
| Deployment | Azure Container Apps |
| Monitoring | Custom middleware + drift detection |

---

## 3. Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    Frontend (React)                          │
└─────────────────────────┬───────────────────────────────────┘
                          │ HTTP/REST
┌─────────────────────────▼───────────────────────────────────┐
│                  FastAPI Application                         │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────┐  │
│  │   Auth   │ │   Jobs   │ │ Resumes  │ │  Interviews  │  │
│  │  (JWT)   │ │  (CRUD)  │ │ (Upload) │ │  (AI-Eval)   │  │
│  └──────────┘ └──────────┘ └──────────┘ └──────────────┘  │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────┐  │
│  │  Search  │ │  Voice   │ │  Graph   │ │     Ops      │  │
│  │ (Hybrid) │ │(Whisper) │ │  (RAG)   │ │ (Monitoring) │  │
│  └──────────┘ └──────────┘ └──────────┘ └──────────────┘  │
└───┬──────────────┬──────────────┬──────────────┬────────────┘
    │              │              │              │
┌───▼───┐   ┌─────▼─────┐  ┌────▼────┐   ┌────▼────┐
│Postgre│   │  Qdrant   │  │  Neo4j  │   │ OpenAI  │
│  SQL  │   │(Vectors)  │  │ (Graph) │   │  APIs   │
└───────┘   └───────────┘  └─────────┘   └─────────┘
```

---

## 4. Database Schema (PostgreSQL)

### Entity Relationship

```
Users (id, email, hashed_password, full_name, role, is_active, phone)
  │
  ├── Candidates (id, user_id, headline, skills[], experience_years, education[])
  │     │
  │     ├── Resumes (id, candidate_id, file_path, status, extracted_skills[], parsed_data)
  │     │
  │     └── JobApplications (id, job_id, candidate_id, status, match_score)
  │           │
  │           └── Interviews (id, application_id, type, status, questions[], responses[])
  │                 │
  │                 └── Evaluations (id, interview_id, overall_score, strengths[], recommendation)
  │
  └── Jobs (id, title, description, required_skills[], status, created_by)
```

### Models
- **Users** — HR, Candidate, Admin roles with RBAC
- **Candidates** — Profile with skills, experience, education (JSON fields)
- **Jobs** — Job descriptions with required/preferred skills
- **JobApplications** — Links candidates to jobs with match scores
- **Resumes** — File metadata + parsed NLP data
- **Interviews** — AI-generated questions + candidate responses
- **Evaluations** — Multi-dimensional scoring with explainable recommendations

---

## 5. API Endpoints (62 Total)

### 5.1 Authentication (4 endpoints)
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /api/v1/auth/register | Register new user (HR/Candidate) |
| POST | /api/v1/auth/login | Login and receive JWT tokens |
| POST | /api/v1/auth/refresh | Refresh access token |
| GET | /api/v1/auth/me | Get current user profile |

### 5.2 Users (5 endpoints)
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /api/v1/users/ | List users (HR/Admin only) |
| GET | /api/v1/users/{id} | Get specific user |
| PUT | /api/v1/users/me | Update profile |
| POST | /api/v1/users/me/change-password | Change password |
| DELETE | /api/v1/users/{id} | Deactivate user (Admin) |

### 5.3 Jobs (7 endpoints)
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /api/v1/jobs/ | Create job description |
| GET | /api/v1/jobs/ | List jobs (filtered by role) |
| GET | /api/v1/jobs/{id} | Get job details |
| PUT | /api/v1/jobs/{id} | Update job |
| DELETE | /api/v1/jobs/{id} | Delete job |
| POST | /api/v1/jobs/{id}/apply | Candidate applies to job |
| GET | /api/v1/jobs/{id}/applications | List applications |

### 5.4 Resumes (6 endpoints)
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /api/v1/resumes/upload | Upload resume (PDF/DOCX/TXT) |
| POST | /api/v1/resumes/{id}/parse | Parse resume with NLP |
| GET | /api/v1/resumes/ | List resumes |
| GET | /api/v1/resumes/{id} | Get resume details |
| POST | /api/v1/resumes/match-jd | Match candidates to JD |
| POST | /api/v1/resumes/search | BM25 lexical search |

### 5.5 Search & Ranking (5 endpoints)
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /api/v1/search/semantic | Vector semantic search |
| POST | /api/v1/search/hybrid | BM25 + Vector hybrid search |
| POST | /api/v1/search/index-resume | Index resume in vector DB |
| POST | /api/v1/search/index-all | Batch index all resumes |
| GET | /api/v1/search/vector-stats | Vector DB statistics |

### 5.6 Notifications (3 endpoints)
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /api/v1/notifications/shortlisted | Send shortlist email |
| POST | /api/v1/notifications/interview-invite | Send interview invite |
| POST | /api/v1/notifications/bulk-notify | Bulk notifications |

### 5.7 Analytics (5 endpoints)
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /api/v1/analytics/overview | Dashboard metrics |
| GET | /api/v1/analytics/job-pipeline/{id} | Job hiring pipeline |
| GET | /api/v1/analytics/skills | Skill distribution |
| GET | /api/v1/analytics/experience | Experience distribution |
| GET | /api/v1/analytics/funnel | Hiring funnel |

### 5.8 Interviews & Evaluation (6 endpoints)
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /api/v1/interviews/generate-questions | AI question generation |
| POST | /api/v1/interviews/submit-responses | Submit answers |
| POST | /api/v1/interviews/evaluate | AI evaluation |
| POST | /api/v1/interviews/rerank | Re-rank after interview |
| GET | /api/v1/interviews/{id} | Get interview details |
| GET | /api/v1/interviews/by-application/{id} | List interviews |

### 5.9 Voice Interview (4 endpoints)
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /api/v1/voice/create-session | Start voice session |
| POST | /api/v1/voice/upload-response | Upload audio answer |
| POST | /api/v1/voice/transcribe/{id} | Whisper transcription |
| GET | /api/v1/voice/status | Service status |

### 5.10 Knowledge Graph & Graph RAG (9 endpoints)
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /api/v1/graph/status | Graph DB status |
| GET | /api/v1/graph/related-skills/{skill} | Find related skills |
| POST | /api/v1/graph/add-skill | Add skill to graph |
| POST | /api/v1/graph/add-relationship | Create skill relationship |
| POST | /api/v1/graph/index-candidate/{id} | Index candidate |
| POST | /api/v1/graph/index-job/{id} | Index job |
| POST | /api/v1/graph/skill-gap | Skill gap analysis |
| POST | /api/v1/graph/evaluate | Graph RAG evaluation |
| POST | /api/v1/graph/recommendations | Learning path |

### 5.11 Operations & Monitoring (6 endpoints)
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /api/v1/ops/health | Detailed health check |
| GET | /api/v1/ops/metrics | Latency & request metrics |
| GET | /api/v1/ops/drift | Model drift detection |
| POST | /api/v1/ops/check-prompt | Prompt injection check |
| GET | /api/v1/ops/costs | API cost summary |
| GET | /api/v1/ops/audit-logs | Audit trail |

---

## 6. AI/ML Components

### 6.1 Resume Parsing (NLP)
- **Tokenization** — NLTK word_tokenize
- **Lemmatization** — NLTK WordNetLemmatizer
- **Stop-word Removal** — NLTK English stopwords
- **Named Entity Recognition** — spaCy en_core_web_sm
- **Extraction**: Name, Email, Phone, Skills, Experience, Education

### 6.2 Search & Ranking
- **BM25 (Lexical)** — Term frequency-based ranking
- **Vector Search (Semantic)** — 384-dim embeddings, cosine similarity
- **Hybrid Search** — Configurable weights (BM25 35% + Vector 45% + Skills 20%)
- **ANN/HNSW** — Qdrant's internal indexing for fast retrieval

### 6.3 AI Interview System
- **Question Generation** — Prompt engineering with context augmentation
- **Difficulty Adjustment** — easy/medium/hard/mixed
- **Categories** — Technical, Behavioral, Situational, Problem-solving
- **Evaluation** — Multi-dimensional (technical, communication, problem-solving)
- **Faithfulness Scoring** — Detects vague/overconfident responses
- **Explainable Recommendations** — hire/maybe/reject with justification

### 6.4 Graph RAG
- **Knowledge Graph** — Skills, relationships, hierarchies
- **Graph Traversal** — Find related skills within N hops
- **Skill Gap Analysis** — Matched vs missing vs transferable skills
- **Graph-Enhanced Evaluation** — Context-enriched recommendations
- **Learning Path** — Identifies skills easy to learn based on existing knowledge

### 6.5 Voice Interview
- **Audio Upload** — MP3, WAV, WebM, OGG, M4A
- **Whisper STT** — OpenAI Whisper API for transcription
- **Segment-level Timing** — Per-sentence timestamps
- **Auto-evaluation** — Transcripts fed to AI evaluator

---

## 7. Security & Governance

- **JWT Authentication** — Access + Refresh tokens
- **RBAC** — Admin, HR, Candidate roles with endpoint-level guards
- **Password Hashing** — bcrypt
- **Prompt Injection Protection** — Pattern detection + sanitization
- **Cost Monitoring** — Per-model token usage tracking
- **Audit Logging** — All actions recorded with timestamps
- **Input Validation** — Pydantic schemas for all requests

---

## 8. DevOps & Deployment

### Docker
```bash
docker-compose up   # PostgreSQL + App (auto-migration)
```

### CI/CD Pipeline (GitHub Actions)
1. **Lint** — ruff + mypy
2. **Test** — pytest with PostgreSQL service
3. **Build** — Docker image → GitHub Container Registry
4. **Deploy** — Azure Container Apps

### Environment Variables
```
DATABASE_URL=postgresql://user:pass@host:5432/db
SECRET_KEY=your-secret-key
OPENAI_API_KEY=sk-...          # Optional: enables LLM features
QDRANT_HOST=localhost           # Optional: defaults to in-memory
NEO4J_URI=bolt://localhost:7687 # Optional: falls back to rule-based
SMTP_HOST=smtp.gmail.com       # Optional: enables email
```

---

## 9. Setup Instructions

### Local Development
```bash
cd ai-talent-platform
python -m venv venv
.\venv\Scripts\activate          # Windows
pip install -r requirements.txt
python -m spacy download en_core_web_sm
copy .env.example .env           # Edit with your settings
uvicorn app.main:app --reload --port 8000
```

### With Docker (Recommended)
```bash
docker-compose up --build
# App: http://localhost:8000
# Docs: http://localhost:8000/docs
```

### Run Tests
```bash
pytest tests/ -v
```

---

## 10. Sprint Roadmap Summary

| Sprint | Week | Goal | Story Points | Endpoints |
|--------|------|------|-------------|-----------|
| 1 | Week 1 | Foundation (Auth + DB + APIs) | 26 | 16 |
| 2 | Week 2 | Resume Intelligence (NLP + BM25) | 26 | 6 |
| 3 | Week 3 | Semantic Search & Ranking | 34 | 13 |
| 4 | Week 4 | GenAI Evaluation | 26 | 6 |
| 5 | Week 5 | Voice Interview + Graph RAG | 42 | 13 |
| 6 | Week 6 | MLOps & Deployment | 60 | 8 |
| **Total** | | | **~214** | **62** |

---

## 11. Project Structure

```
ai-talent-platform/
├── app/
│   ├── main.py                      # FastAPI entry point
│   ├── core/
│   │   ├── config.py                # Settings (env-based)
│   │   ├── security.py              # JWT + password hashing
│   │   ├── dependencies.py          # Auth + RBAC dependencies
│   │   └── middleware.py            # Latency tracking
│   ├── api/v1/
│   │   ├── router.py               # Route aggregator
│   │   └── endpoints/
│   │       ├── auth.py              # Login, register
│   │       ├── users.py             # User management
│   │       ├── jobs.py              # Job CRUD + apply
│   │       ├── resumes.py           # Upload, parse, match
│   │       ├── search.py            # Semantic + hybrid search
│   │       ├── notifications.py     # Email automation
│   │       ├── analytics.py         # Dashboard data
│   │       ├── interviews.py        # AI questions + evaluation
│   │       ├── voice.py             # Voice interview
│   │       ├── graph.py             # Knowledge graph + RAG
│   │       └── ops.py              # Monitoring + governance
│   ├── models/                      # SQLAlchemy ORM (6 models)
│   ├── schemas/                     # Pydantic validation
│   ├── services/                    # Business logic (10 services)
│   │   ├── resume_parser.py         # NLP extraction
│   │   ├── jd_matcher.py           # BM25 matching
│   │   ├── embedding_service.py     # Vector embeddings
│   │   ├── vector_store.py          # Qdrant operations
│   │   ├── hybrid_search.py        # Combined search
│   │   ├── llm_service.py          # OpenAI/Azure wrapper
│   │   ├── question_generator.py    # AI question gen
│   │   ├── evaluation_service.py    # AI evaluation
│   │   ├── reranking_service.py    # Post-interview ranking
│   │   ├── voice_service.py        # Whisper STT
│   │   ├── knowledge_graph.py      # Neo4j graph
│   │   ├── graph_rag.py            # Graph RAG
│   │   ├── email_service.py        # SMTP notifications
│   │   ├── analytics_service.py    # Metrics
│   │   ├── monitoring.py           # Observability
│   │   └── governance.py           # Security + audit
│   └── db/                          # Database session + base
├── alembic/                         # Database migrations
├── tests/                           # Test suite
├── scripts/                         # Utility scripts
├── uploads/                         # File storage
├── .github/workflows/ci-cd.yml     # GitHub Actions pipeline
├── Dockerfile                       # Container build
├── docker-compose.yml              # Full stack orchestration
├── requirements.txt                # Python dependencies
└── .env.example                    # Environment template
```

---

*Document generated for AI Talent Acquisition Platform v1.0.0*
*Repository: https://github.com/NAVEEN1901/AI_INTERVIEWER_SYSTEM_DESIGN*
