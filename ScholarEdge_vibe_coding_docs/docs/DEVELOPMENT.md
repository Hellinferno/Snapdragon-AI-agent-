# ScholarEdge — Development Guide

## Development machine

Current machine:
- Lenovo ThinkBook 14 G4 IAP
- Intel Core i3-1215U
- 8 GB RAM
- Windows 11 Pro
- x64

The machine is sufficient for application development, document processing, tests, and lightweight AI workloads. It is not the target for heavy local LLM/vision inference.

## Initial setup

Expected tools:
- Git
- Python 3.11+ or the version pinned by the project
- Node.js LTS
- npm
- a virtual environment for Python

## Setup principle

Keep the environment lightweight. Do not install large model weights until a feature actually requires them.

## Local services

The MVP should avoid mandatory external infrastructure.

Preferred:
- SQLite for metadata
- local vector store
- local filesystem for development documents

## Configuration

Use environment variables for:
- provider selection
- model identifiers
- optional API credentials
- storage paths
- debug flags

Never commit `.env`.

Use `.env.example` with safe placeholder names only.

## Running

The exact commands belong here once the repository is scaffolded and tested.

Expected development shape:

```text
backend → FastAPI
frontend → React/Vite
```

## Performance constraints

Because the development machine has 8 GB RAM:
- avoid loading multiple large models;
- process documents incrementally;
- release temporary tensors/files;
- avoid duplicate copies of large documents;
- prefer small embedding models;
- make external LLM usage optional rather than mandatory.

## Snapdragon development

Snapdragon-specific implementation is a later phase.

The development machine should still run the same application through a development provider.
