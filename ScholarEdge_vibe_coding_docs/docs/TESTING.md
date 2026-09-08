# ScholarEdge — Testing Strategy

## Goals

Testing should prove:
1. documents are processed correctly;
2. metadata is preserved;
3. retrieval returns relevant evidence;
4. generated answers expose sources;
5. provider substitution does not break application logic.

## Test layers

### Unit tests
Test:
- PDF/page extraction adapters
- chunking
- metadata creation
- embedding adapters
- retrieval logic
- prompt/context construction
- comparison formatting
- quiz generation schemas

### Integration tests
Test:
- upload → extraction → indexing
- question → retrieval → generation
- multi-document retrieval
- comparison workflow

### End-to-end tests
At least one test should cover:

```text
upload test PDFs
→ index
→ ask question
→ verify answer structure
→ verify source references
```

## AI evaluation

Do not test only whether an LLM returns text.

Create a small fixed evaluation set containing:
- questions with known answers;
- questions whose evidence exists;
- questions whose evidence does not exist;
- cross-document questions;
- citation/source expectations.

Evaluate:
- retrieval relevance;
- citation presence;
- groundedness;
- refusal/insufficient-evidence behavior;
- latency where measurable.

## Snapdragon benchmarking

Do not mix functional tests with hardware benchmarks.

Benchmark separately:
- model load time
- first inference
- warm inference
- end-to-end latency
- memory
- CPU/NPU utilization when measurable

Never fabricate missing measurements.
