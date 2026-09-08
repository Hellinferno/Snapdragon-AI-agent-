# ScholarEdge

> **Private, on-device AI research and learning copilot.**

ScholarEdge turns research papers, study material, and notes into a searchable knowledge base for grounded research, comparison, and revision.

---

## Current Status: Phase 1 (M0 Foundation + M1 Document Engine)

- [x] **M0 Foundation**:
  - FastAPI asynchronous backend with Pydantic configuration and structured logging
  - SQLite database persistence with async session management
  - Clean AI provider interface abstractions (`EmbeddingProvider`, `LLMProvider`, `OCRProvider`)
  - Automated test suite (`pytest`) with 100% passing tests
  - Continuous Integration workflow (`.github/workflows/ci.yml`)
  - React + Vite modern research studio frontend with dark theme and glassmorphic UI tokens

- [x] **M1 Document Engine**:
  - Validated PDF upload (`POST /api/documents`)
  - Duplicate detection via SHA-256 content hashing
  - Page-aware PDF text extraction preserving 1-based page numbers
  - Section-aware and sliding-window chunking
  - Full source lineage: `Document` -> `Page` -> `Chunk`
  - Document management: listing, detail viewing, chunk inspection, and cascading deletion (`DELETE /api/documents/{id}`)
  - Library UI with drag-and-drop upload, processing state indicators, and chunk inspector modal

---

## Project Structure

```text
snapdragon/
├── .github/
│   └── workflows/
│       └── ci.yml               # Automated CI pipeline
├── backend/
│   ├── app/
│   │   ├── api/                 # FastAPI routes (health, documents)
│   │   ├── core/                # Settings, database, logging
│   │   ├── models/              # SQLite SQLAlchemy models (Document, Page, Chunk)
│   │   ├── providers/           # Replaceable AI provider interfaces
│   │   ├── schemas/             # Pydantic request/response schemas
│   │   ├── services/            # PDF parser, chunker, document orchestration
│   │   └── main.py              # Application entry point & CORS
│   ├── tests/                   # Unit and integration tests
│   ├── requirements.txt
│   └── pyproject.toml
├── frontend/
│   ├── src/
│   │   ├── api.js               # Backend API client
│   │   ├── App.jsx              # Main Research Studio & Library UI
│   │   ├── index.css            # Dark theme design system tokens
│   │   └── main.jsx
│   ├── index.html
│   ├── package.json
│   └── vite.config.js
└── ScholarEdge_vibe_coding_docs/# Specifications & architecture documentation
```

---

## Quick Start

### 1. Backend Setup

```bash
cd backend
python -m venv .venv
.\.venv\Scripts\activate      # Windows
pip install -r requirements.txt
pytest -v                     # Run test suite
uvicorn app.main:app --reload --port 8000
```

Interactive API docs available at: `http://localhost:8000/docs`

### 2. Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

Application available at: `http://localhost:5173`
