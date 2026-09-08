# Contributing to ScholarEdge

## Development philosophy

ScholarEdge is a competition project, but the code should be treated like a real product. Prefer a small, reliable system over a large collection of half-working AI features.

## Contribution rules

- Keep pull requests focused.
- Do not commit secrets, API keys, private documents, or personal data.
- Add tests for new behavior and bug fixes.
- Avoid unrelated refactors.
- Update relevant documentation when behavior changes.
- Do not claim hardware/model support without verification.
- Preserve source metadata throughout document and RAG pipelines.

## Commit style

Use concise, action-oriented commits, for example:

```text
feat: add page-aware PDF ingestion
fix: preserve source page during retrieval
test: cover empty retrieval results
docs: document embedding provider interface
```

## Pull request checklist

- [ ] Scope is focused.
- [ ] Tests added/updated.
- [ ] Relevant tests pass.
- [ ] No secrets or private data.
- [ ] Documentation updated if needed.
- [ ] No unverified Snapdragon/Qualcomm claims.
