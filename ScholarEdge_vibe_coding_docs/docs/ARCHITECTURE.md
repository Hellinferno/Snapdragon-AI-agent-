# ScholarEdge — Architecture

## System overview

```text
                    ┌─────────────────────┐
                    │      React UI       │
                    └──────────┬──────────┘
                               │ HTTP
                    ┌──────────▼──────────┐
                    │     FastAPI API     │
                    └──────────┬──────────┘
                               │
          ┌────────────────────┼────────────────────┐
          │                    │                    │
          ▼                    ▼                    ▼
   Document Service      Retrieval Service    Research/Learning
          │                    │                    │
          ▼                    ▼                    │
   Parser/OCR            Vector Store              │
          │                    │                    │
          └──────────────┬─────┘                    │
                         ▼                          │
                  AI Provider Layer ◄───────────────┘
                         │
          ┌──────────────┼──────────────┐
          ▼              ▼              ▼
         LLM        Embeddings         Vision
          │
   Development backend
   or Snapdragon backend
```

## Architectural boundaries

### UI
Responsible for:
- interaction,
- document/library display,
- chat,
- source display,
- research workflows,
- learning workflows.

The UI should not directly call model SDKs.

### API
Responsible for:
- validation,
- request orchestration,
- authorization if introduced later,
- returning structured application data.

### Document service
Responsible for:
- file validation,
- PDF parsing,
- page-aware extraction,
- chunking,
- metadata creation.

### Retrieval service
Responsible for:
- embedding queries,
- vector search,
- ranking/filtering,
- returning source-aware chunks.

### AI provider layer
Responsible for:
- generation,
- embeddings,
- OCR,
- vision,
- speech.

Providers are replaceable.

## Data flow: ingestion

```text
PDF
 ↓
validate
 ↓
extract page text
 ↓
OCR only where needed
 ↓
normalize
 ↓
chunk
 ↓
attach metadata
 ↓
embed
 ↓
store metadata + vectors
```

## Data flow: question answering

```text
question
 ↓
query embedding
 ↓
vector retrieval
 ↓
source-aware context
 ↓
LLM
 ↓
answer + sources
```

## Hardware portability

The application must not depend on a particular CPU/GPU/NPU.

Hardware-specific inference belongs below provider interfaces:

```text
Application
    ↓
Provider interface
    ↓
Development backend / Qualcomm backend
```

This lets the application be developed on the current ThinkBook and later validated on Snapdragon hardware.
