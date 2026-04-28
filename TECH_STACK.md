# Technology Stack — Unisco RAG System

This document explains every technology used in the system and the reason it was chosen, along with how all the pieces fit together end-to-end.

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      API Layer (FastAPI)                    │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │  Search API  │  │ Feedback API │  │ Health Check │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
└─────────────────────────────────────────────────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        │                   │                   │
┌───────▼────────┐  ┌───────▼────────┐  ┌───────▼────────┐
│  Hybrid        │  │  LLM Handler   │  │  Redis Cache   │
│  Retriever     │  │ (Claude 3.5)   │  │                │
└───────┬────────┘  └───────┬────────┘  └───────┬────────┘
        │                   │                   │
        │         ┌─────────┴──────────┐        │
        │         │                    │        │
┌───────▼─────────▼───────┐  ┌────────▼───────────────┐
│  Elasticsearch           │  │  Document Storage      │
│  (Hybrid Search)         │  │  (Local / S3)          │
│  - Keyword (BM25)        │  │                        │
│  - Semantic (BGE-M3)     │  │                        │
└──────────────────────────┘  └────────────────────────┘
```

---

## Document Ingestion Flow

When a document is uploaded it goes through the following steps before it can be queried:

```
1. Document Upload (PDF, DOCX, or TXT)
        ↓
2. LlamaParse extracts text + structure (page-level chunks)
        ↓
3. Metadata captured per chunk
   (document_id, company_id, page_number, section_title)
        ↓
4. BGE-M3 generates a 1024-dimension embedding per chunk
        ↓
5. Chunks + embeddings indexed in Elasticsearch
        ↓
6. Original file saved to document storage (local or S3)
```

---

## Query Flow

When a user submits a question:

```
1. Query received at POST /api/v1/search
        ↓
2. Check Redis cache  ──── Cache HIT ──→ Return cached response (< 50 ms)
        │ Cache MISS
        ↓
3. Hybrid search runs in parallel
   ├── Keyword search  (BM25 over chunk_text, section_title)
   └── Semantic search (cosine similarity via BGE-M3 embedding)
        ↓
4. Reciprocal Rank Fusion (RRF) merges + deduplicates results
        ↓
5. Top N chunks selected as context
        ↓
6. Claude 3.5 Sonnet generates a grounded answer with citations
        ↓
7. Response formatted  (answer + citations + metadata)
        ↓
8. Result stored in Redis (TTL: 1 hour)
        ↓
9. Response returned to user (target: < 500 ms p95)
```

---

## 1. Document Parsing: LlamaParse (+ PyMuPDF fallback)

**Why LlamaParse:**
- Produces structured markdown output from PDFs, making it significantly easier to extract headers, tables, and section boundaries
- Superior at pulling page numbers, section titles, and document metadata — all essential for accurate citations
- Understands document layout and formatting better than text-extraction-only tools

**Why PyMuPDF as fallback:**
- 10–20x faster than alternatives like pdfminer or PyPDF2
- Activates automatically when no LlamaParse API key is provided, keeping the system functional without the cloud dependency

---

## 2. Search Engine: Elasticsearch

**Why Elasticsearch over Solr or standalone vector databases:**
- Natively supports both keyword (BM25) and dense vector (semantic) search in a single query — no need to stitch together two separate systems
- Excellent metadata filtering, which is how the system enforces company-level data isolation (every query is scoped to a `company_id`)
- Scales efficiently to handle multiple large documents (2–20 MB each) across many companies

---

## 3. Embedding Model: BGE-M3

**Why BGE-M3 over Sentence-BERT or OpenAI embeddings:**
- Produces 1024-dimension dense vectors with state-of-the-art semantic understanding
- Supports 100+ languages out of the box — useful for logistics companies operating internationally
- Open-source with no per-call API cost, unlike OpenAI embeddings
- Stored directly in Elasticsearch alongside document chunks, enabling efficient cosine similarity queries

---

## 4. Retrieval Strategy: Hybrid Search with Reciprocal Rank Fusion (RRF)

**Why hybrid instead of keyword-only or semantic-only:**
- Logistics users sometimes search with exact terminology ("OSHA 1910.178") and sometimes with natural language ("how do I operate a forklift safely") — hybrid handles both
- Keyword search (BM25) catches precise matches; semantic search catches synonyms and paraphrasing
- Both searches run in parallel, so there is no added latency from combining them

**Why RRF for combining results:**
- Simple formula: `Score = Σ(1 / (k + rank))` — no training data required
- Merges ranked lists from keyword and semantic search without needing raw relevance scores to be on the same scale
- Industry-standard `k=60` constant provides stable, well-tested results

---

## 5. Generative Model: Claude 3.5 Sonnet

**Why Claude 3.5 Sonnet over GPT-4 or local LLMs:**
- Exceptionally strong at synthesizing answers from multiple retrieved document chunks into a single coherent response
- Stays grounded in the provided context — less likely to hallucinate or add information not present in the documents
- Reliable at referencing specific document sections and page numbers in its output, which directly supports the citation requirement
- Temperature set to **0.3** to favour factual, consistent answers over creative variation

---

## 6. Caching: Redis

**Why Redis over Memcached or in-process caches:**
- Sub-millisecond read latency — cache hits return in under 50 ms, well below the 500 ms response target
- Supports complex data structures, allowing full response JSON (including citations and metadata) to be stored and retrieved atomically
- Optional persistence means the cache can survive a service restart
- Cache keys are formatted as `search:{company_id}:{query_hash}` using an MD5 of the normalized query, so minor variations in spacing or casing still resolve to the same cached result
- TTL of 1 hour balances freshness against performance — documentation doesn't change frequently, so stale results are an acceptable trade-off

---

## 7. API Framework: FastAPI

**Why FastAPI over Flask or Django:**
- Async-first design allows the server to handle concurrent requests without blocking — critical for the 100 req/sec throughput target
- Automatic OpenAPI documentation is generated from the code, making integration straightforward for other teams
- Built-in Pydantic validation provides type-safe request and response parsing, with clear error messages on invalid input
- Lightweight and purpose-built for APIs — Django's ORM and admin overhead are unnecessary here

---

## Summary Table

| Layer | Technology | Core Reason |
|---|---|---|
| Document Parsing | LlamaParse + PyMuPDF | Best structure extraction + citation metadata; fast fallback |
| Search Engine | Elasticsearch | Native hybrid search + company-level filtering in one system |
| Embeddings | BGE-M3 | High-quality, multilingual, open-source, no API cost |
| Retrieval | Hybrid BM25 + Dense Vector + RRF | Handles both exact and natural language queries |
| Generation | Claude 3.5 Sonnet | Grounded synthesis, strong citation capability |
| Caching | Redis | Sub-ms latency, complex value storage, 1-hour TTL |
| API | FastAPI | Async throughput, auto-docs, Pydantic validation |
