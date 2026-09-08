# ScholarEdge

**Private, on-device AI research and learning copilot.**

ScholarEdge is being built to turn research papers, study material, notes, and visual content into a searchable knowledge base for research, explanation, comparison, and revision.

## Why it exists

Students and researchers often have useful information scattered across PDFs, lecture notes, papers, screenshots, and scanned documents. ScholarEdge aims to make that material queryable while keeping the architecture suitable for privacy-first, on-device AI.

## Core workflow

```text
Documents
   ↓
Parsing / OCR
   ↓
Page-aware chunks + metadata
   ↓
Embeddings
   ↓
Local vector retrieval
   ↓
Grounded RAG
   ↓
Research / Learning workflows
```

## MVP

- Upload and process PDFs
- Page-aware text extraction
- Local semantic retrieval
- Source-grounded Q&A
- Multi-paper Q&A
- Paper comparison
- Concept explanations
- Quiz generation

## Planned extensions

- Research-paper figure understanding
- Screenshot understanding
- OCR for scanned material
- Knowledge graph
- Voice interaction
- Handwriting OCR
- Snapdragon-specific AI model/runtime deployment and benchmarking

## Architecture

See:
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)
- [`docs/PROJECT_SPEC.md`](docs/PROJECT_SPEC.md)
- [`docs/AI_MODELS.md`](docs/AI_MODELS.md)
- [`docs/SNAPDRAGON.md`](docs/SNAPDRAGON.md)

## Development

See [`docs/DEVELOPMENT.md`](docs/DEVELOPMENT.md).

## Testing

See [`docs/TESTING.md`](docs/TESTING.md).

## Status

Early development. Features must not be described as complete until they are implemented and verified.

## Important

Snapdragon/Qualcomm claims in this repository are deployment targets unless backed by verified device/runtime tests. Never use benchmark numbers copied from marketing material as project benchmarks.
