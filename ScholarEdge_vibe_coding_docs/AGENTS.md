# ScholarEdge — AI Coding Agent Instructions

## Mission
Build ScholarEdge as a privacy-first research and learning copilot designed for eventual deployment on Snapdragon-powered HP PCs.

The product turns papers, notes, and visual study material into a searchable knowledge base and provides grounded research and learning assistance.

## Non-negotiable engineering principles
1. Build working functionality before adding polish.
2. Do not invent Qualcomm/Snapdragon support. Only claim hardware/runtime/model support after verification.
3. Keep AI providers behind interfaces so development and Snapdragon deployments can use different backends.
4. Prefer local-first processing and storage. Never send user documents to a remote service unless the user explicitly configured an external provider.
5. Every RAG answer must preserve source metadata and expose citations where available.
6. Never silently fabricate citations, paper content, benchmark results, model capabilities, or hardware performance.
7. Optimize for the user's 8 GB RAM development machine: avoid unnecessarily loading large models.
8. Keep components small, typed, testable, and independently replaceable.
9. Do not add a dependency without a concrete reason.
10. Do not implement future features just to populate the repository.

## Current development target
The development machine is a Lenovo ThinkBook 14 G4 IAP:
- Intel Core i3-1215U
- 8 GB RAM
- Windows 11 Pro
- x64

The target deployment is Snapdragon-powered Windows PCs. Snapdragon-specific work must be isolated behind provider/runtime interfaces.

## Product scope
### MVP
- PDF ingestion
- Text extraction
- Page-aware chunking
- Embeddings
- Local vector retrieval
- RAG Q&A
- Page/source citations
- Multi-document Q&A
- Paper comparison
- Concept explanation
- Quiz generation

### Post-MVP
- Figure/screenshot understanding
- OCR for scanned documents
- Knowledge graph
- Voice input
- Handwriting OCR
- Snapdragon NPU optimization and benchmarking

## Architecture rules
- Backend: Python + FastAPI.
- Frontend: React + Vite.
- Metadata: SQLite.
- Vector storage: local vector database; keep the implementation replaceable.
- AI: provider abstraction.
- Document processing: modular pipeline.
- Tests live near the code they validate or in the established test tree.
- Configuration comes from environment/config files, never hard-coded secrets.

## AI provider contract
All generation, embedding, OCR, vision, and speech integrations must have explicit interfaces.

Example conceptual interfaces:
- `LLMProvider`
- `EmbeddingProvider`
- `OCRProvider`
- `VisionProvider`
- `SpeechToTextProvider`

The application layer must depend on interfaces, not a specific model SDK.

## RAG correctness
Every indexed chunk should retain:
- document ID
- page number
- section when known
- chunk ID
- source text
- source location
- document metadata

Retrieval should return source metadata alongside text.

The answer generator must receive retrieved evidence and should be instructed to answer from evidence. If evidence is insufficient, the system should say so.

## Snapdragon rules
Do not use phrases such as:
- "NPU accelerated"
- "Snapdragon optimized"
- "Qualcomm validated"
- "runs on Snapdragon"

unless the repository contains the corresponding verified implementation/test evidence.

Snapdragon integration belongs behind the provider/runtime boundary.

## Coding workflow
For every feature:
1. Read the relevant spec.
2. Define the smallest useful behavior.
3. Write/update tests first when practical.
4. Implement.
5. Run targeted tests.
6. Run the broader test suite.
7. Update documentation only after behavior is verified.
8. Do not mark a task complete without evidence.

## Definition of done
A feature is done only when:
- required behavior works,
- tests cover important paths,
- errors are handled,
- no secrets are committed,
- docs match the implementation,
- relevant tests pass.

## Avoid
- premature microservices
- unnecessary agents
- custom model training
- cloud infrastructure for MVP
- authentication before it is needed
- social features
- autonomous browsing
- fake benchmark data
- decorative UI that obscures the core workflow
