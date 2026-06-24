# RAG Pipeline - AI Talent Acquisition Platform

## Architecture
```
Query/Resume Text
       |
       v
[Embedding Service] --> all-MiniLM-L6-v2 (384-dim vectors)
       |
       v
+------------------+
|  RETRIEVAL LAYER |
+------------------+
|  BM25 Lexical   |  (jd_matcher.py)        - 35% weight
|  Vector Search  |  (vector_store.py)      - 45% weight  
|  Skill Match    |  (knowledge_graph.py)   - 20% weight
+------------------+
       |
       v
[Hybrid Search] --> Combines all 3 retrieval sources
       |
       v
[Graph RAG] --> Augments context with skill graph relationships
       |
       v
[LLM Service] --> OpenAI/Azure OpenAI generates final answer
       |
       v
Evaluation / Recommendation / Ranking
```

## Files

| File | Role | Description |
|------|------|-------------|
| embedding_service.py | Embed | Converts text to 384-dim vectors using all-MiniLM-L6-v2 |
| vector_store.py | Store & Retrieve | Qdrant vector DB (with in-memory fallback) |
| jd_matcher.py | Lexical Retrieve | BM25 search + skill matching + experience scoring |
| hybrid_search.py | Hybrid | Combines BM25 (35%) + Vector (45%) + Skills (20%) |
| knowledge_graph.py | Graph | Neo4j skill relationships (with rule-based fallback) |
| graph_rag.py | RAG Core | Graph-enhanced retrieval + augmentation + generation |
| llm_service.py | Generate | OpenAI/Azure LLM wrapper for answer generation |

## How RAG Works Here

1. **Retrieve**: When HR searches for candidates or evaluates them:
   - BM25 finds keyword matches in resumes
   - Vector search finds semantically similar candidates
   - Knowledge graph finds related skills

2. **Augment**: Graph RAG enriches the context:
   - Adds skill relationships (Python -> FastAPI, Django)
   - Identifies transferable skills
   - Calculates skill gaps

3. **Generate**: LLM produces:
   - Candidate evaluations with explanations
   - Interview questions personalized to skills
   - Hiring recommendations with reasoning

## Requirements
```
sentence-transformers
qdrant-client
numpy
rank-bm25
nltk
openai  # optional - for LLM generation
neo4j   # optional - for graph database
```

## Usage Example
```python
from rag_pipeline.embedding_service import generate_embedding
from rag_pipeline.hybrid_search import hybrid_search
from rag_pipeline.graph_rag import graph_rag_service

# 1. Generate embedding for a query
query = "Python developer with ML experience"
embedding = generate_embedding(query)

# 2. Hybrid search (BM25 + Vector + Skills)
results = hybrid_search.search(query, required_skills=["python", "ml"])

# 3. Graph RAG evaluation
evaluation = graph_rag_service.generate_enhanced_evaluation(
    candidate_skills=["python", "tensorflow", "sql"],
    candidate_experience=3.0,
    job_title="ML Engineer",
    job_required_skills=["python", "pytorch", "mlops"],
)
```
