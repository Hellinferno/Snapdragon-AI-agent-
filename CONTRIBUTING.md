# Contributing to ScholarEdge

Thank you for your interest in contributing to ScholarEdge!

---

## 1. Core Principles & Coding Standards

1. **Truth in Telemetry**: Never report `Hexagon NPU Active` unless `QNNExecutionProvider` is physically loaded and active in the ONNX runtime session.
2. **Strict Source Grounding**: All synthesis and responses must trace back to indexed source chunks. If evidence is lacking, refuse explicitly.
3. **Local-First & Privacy Compliance**: Code additions must not introduce telemetry calls or default network egress to cloud APIs.
4. **Memory Constraint**: The backend must run comfortably within an 8 GB RAM envelope (< 500 MB RSS).

---

## 2. Development & Pull Request Workflow

1. Fork and clone the repository.
2. Create a feature branch:
   ```bash
   git checkout -b feature/my-improvement
   ```
3. Set up the Python virtual environment and run the test suite:
   ```bash
   cd backend
   pytest -v
   ```
   **All tests must pass before submitting a PR.**
4. Check frontend build:
   ```bash
   cd ../frontend
   npm run build
   ```
5. Commit your changes with descriptive commit messages.
6. Push to your branch and open a Pull Request against `main`.
