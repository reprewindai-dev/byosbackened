---
name: rag-agent
description: Playbook for RAG knowledge agents (108-113). Covers document indexing, semantic search, knowledge synthesis, agent memory, and support RAG.
---

# RAG Knowledge Agent Playbook

## When to Use
Invoke this skill when spinning up any RAG knowledge agent (Agent-108 through Agent-113).

## Prerequisites
- Access to `byosbackened` repo
- Python 3.11+ with embedding libraries
- PostgreSQL with pgvector extension (or similar vector store)
- Ollama/Groq for local LLM inference

## Setup Steps

1. Read your agent mission file from `agents/rag-knowledge/agent-{ID}-{name}.md`
2. Read `MASTER_STATE.md` for current knowledge infrastructure state
3. Review existing AI/LLM integration:
   ```
   backend/app/services/ai_service.py    # Ollama/Groq integration
   backend/app/services/embedding.py     # Vector embeddings
   backend/app/models/                   # Database models
   ```

## Agent Assignments

### Agent-108 (RAG Lead)
- Coordinate RAG pipeline architecture
- Define chunking strategies and retrieval parameters
- Key decisions: chunk size, overlap, embedding model

### Agent-109 (Document Indexer)
- Build document ingestion pipeline
- Support formats: Markdown, PDF, JSON, YAML, code files
- Chunking strategy: semantic paragraphs with overlap

```python
# Document indexing pipeline
from langchain.text_splitter import RecursiveCharacterTextSplitter

splitter = RecursiveCharacterTextSplitter(
    chunk_size=512,
    chunk_overlap=64,
    separators=["\n\n", "\n", ". ", " "]
)
chunks = splitter.split_documents(documents)
```

### Agent-110 (Semantic Search)
- Implement vector similarity search
- Build hybrid search (vector + keyword)
- Optimize retrieval relevance

```python
# Semantic search query
results = vector_store.similarity_search_with_score(
    query="How to configure Stripe Connect",
    k=5,
    score_threshold=0.7
)
```

### Agent-111 (Knowledge Synthesizer)
- Combine retrieved chunks into coherent answers
- Handle multi-document synthesis
- Implement source attribution

### Agent-112 (Agent Memory)
- Persistent memory store for all 120 agents
- Store/retrieve agent context across sessions
- Key: agent_id → memory chunks (decisions, learnings, state)

### Agent-113 (Support RAG)
- Customer-facing knowledge base chatbot
- Index: docs, FAQs, tutorials, API reference
- Serve via `/api/v1/support/chat` endpoint

## RAG Architecture

```
User Query → Embedding → Vector Search → Top-K Chunks
                                              ↓
                                    LLM (Ollama/Groq)
                                              ↓
                                    Synthesized Answer
                                    + Source Citations
```

## Completion Checklist
- [ ] Read mission file and MASTER_STATE.md
- [ ] Implement assigned RAG component
- [ ] Test with sample documents/queries
- [ ] Measure retrieval relevance (target: >80% precision@5)
- [ ] Create PR with implementation
- [ ] Update PROGRESS.md
