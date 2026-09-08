# ScholarEdge — Architecture Decision Record

## ADR-001: FastAPI + React

**Decision:** Use Python/FastAPI for the backend and React/Vite for the frontend.

**Reason:** Gives a clean separation between application logic and UI while remaining lightweight enough for the current development environment.

## ADR-002: Provider abstraction

**Decision:** AI functionality must be accessed through interfaces.

**Reason:** Development happens on an Intel i3 machine, while Snapdragon deployment will use a different runtime/model stack.

## ADR-003: Source-aware RAG

**Decision:** Preserve page/document metadata through the entire retrieval pipeline.

**Reason:** Research software needs traceable evidence. A fluent answer without sources is insufficient.

## ADR-004: Local-first architecture

**Decision:** Avoid mandatory cloud infrastructure for the MVP.

**Reason:** Privacy is a core product differentiator and local-first architecture better matches the Snapdragon on-device story.

## ADR-005: No custom LLM training

**Decision:** Do not train a foundation model.

**Reason:** The competition is about application/use-case development and deployment. Model training would consume resources without strengthening the core product.

## ADR-006: Snapdragon as a deployment backend

**Decision:** Snapdragon-specific code stays below the provider boundary.

**Reason:** Prevents hardware-specific concerns from contaminating the application layer and lets development continue without Snapdragon hardware.
