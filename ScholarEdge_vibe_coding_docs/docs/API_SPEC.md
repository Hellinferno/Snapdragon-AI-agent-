# ScholarEdge — API Specification

This is the intended MVP API contract. Implement only what is needed.

## Documents

### `POST /api/documents`
Upload a document.

Returns:
- document ID
- filename
- processing status

### `GET /api/documents`
List documents.

### `GET /api/documents/{document_id}`
Return document metadata and processing status.

### `DELETE /api/documents/{document_id}`
Delete a document and its derived index data.

## Search

### `POST /api/search`
Input:
- query
- optional collection/document IDs
- top-k

Output:
- source-aware retrieval results.

## Chat

### `POST /api/chat`
Input:
- question
- optional collection/document IDs
- retrieval configuration

Output:
- answer
- source references
- retrieval metadata where appropriate.

## Research

### `POST /api/research/compare`
Input:
- document IDs
- comparison dimensions

Output:
- structured comparison
- supporting source references.

## Learning

### `POST /api/learning/explain`
Input:
- question/concept
- optional document IDs
- desired explanation level

Output:
- explanation
- sources.

### `POST /api/learning/quiz`
Input:
- document/collection IDs
- question count
- difficulty

Output:
- structured quiz.

## API rules

- Validate inputs.
- Return consistent error structures.
- Never expose filesystem paths unnecessarily.
- Never return secrets.
- Keep model/provider implementation details out of public request schemas.
