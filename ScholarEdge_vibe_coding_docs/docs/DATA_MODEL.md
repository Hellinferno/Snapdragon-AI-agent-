# ScholarEdge — Data Model

## Core entities

### Document

Fields:
- `id`
- `filename`
- `title`
- `authors`
- `created_at`
- `status`
- `page_count`
- `content_hash`

### Page

Fields:
- `id`
- `document_id`
- `page_number`
- `text`
- `ocr_used`

### Chunk

Fields:
- `id`
- `document_id`
- `page_id`
- `chunk_index`
- `text`
- `section`
- `embedding_id`

### Collection

Groups documents for research workflows.

### SourceReference

Represents evidence returned to the user.

Fields:
- `document_id`
- `document_title`
- `page_number`
- `chunk_id`
- `relevance_score`

## Requirements

Source metadata must survive:

```text
Document
→ Page
→ Chunk
→ Embedding
→ Retrieval result
→ LLM context
→ UI citation
```

Never store vectors without a way to recover their source.

## Storage

SQLite should contain application metadata.

Vector storage should be local and replaceable.

Large original documents should be stored on the filesystem in development rather than duplicated inside SQLite.
