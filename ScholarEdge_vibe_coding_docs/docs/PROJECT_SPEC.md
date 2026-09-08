# ScholarEdge — Product Specification

## 1. Product statement

ScholarEdge is a private-first AI workspace for research and learning. It ingests academic and study material, builds a source-aware knowledge base, and lets users research, understand, compare, and revise that material.

## 2. Primary user

A student or researcher working with multiple documents who wants:
- fast retrieval,
- grounded explanations,
- paper comparison,
- structured research synthesis,
- study/revision support.

## 3. Primary problem

Existing AI workflows often require users to upload documents to cloud services and treat each document as an isolated chat session. ScholarEdge should instead build a persistent, source-aware local knowledge layer.

## 4. Core use cases

### UC-01: Ingest a paper
User uploads a PDF. The system extracts content while preserving document and page metadata.

### UC-02: Ask a grounded question
User asks a question. The system retrieves relevant chunks and generates an answer grounded in those chunks.

### UC-03: Cross-paper question
User selects a collection of papers and asks a question spanning them.

### UC-04: Compare papers
User selects multiple papers and receives a structured comparison with evidence.

### UC-05: Learn
User asks for an explanation or generates revision questions from the indexed material.

## 5. Trust requirements

- Sources must be visible.
- Page information should be retained whenever available.
- Unsupported claims should be avoided.
- Retrieval failure must not be hidden.
- The UI should distinguish generated explanation from source material.

## 6. MVP acceptance criteria

A test user can:
1. upload at least three PDFs;
2. see successful processing status;
3. ask a question across the documents;
4. receive an answer with source references;
5. compare at least two documents;
6. generate a quiz from the indexed material.

## 7. Non-goals

- medical diagnosis
- financial advice
- autonomous internet research
- general-purpose desktop automation
- model training
- social networking
