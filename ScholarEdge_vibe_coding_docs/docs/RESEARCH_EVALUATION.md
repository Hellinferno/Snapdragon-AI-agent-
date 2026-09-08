# ScholarEdge — Research Evaluation Plan

## Purpose

The competition submission should demonstrate measurable value rather than only a polished interface.

## Evaluation dataset

Create a small, legally usable benchmark collection of public research papers.

Include:
- 3–10 papers for MVP demos;
- known-answer questions;
- cross-paper questions;
- comparison tasks;
- insufficient-evidence questions.

## Retrieval metrics

Track where practical:
- Recall@K
- Precision@K
- source hit rate

## Generation evaluation

Track:
- groundedness;
- citation correctness;
- answer completeness;
- unsupported-claim rate.

Use human evaluation for the final demo if automated evaluation is insufficient.

## Performance evaluation

Track:
- document processing time;
- embedding time;
- retrieval latency;
- model load time;
- first-token/response latency;
- end-to-end response latency;
- memory usage.

For Snapdragon:
- target device;
- CPU/NPU execution;
- runtime;
- precision;
- warm vs cold latency.

## Rule

Performance numbers are valid only when produced by reproducible tests in this repository or clearly labeled as external reference measurements.
