# Developer Guide & Local Setup

This guide details setting up, testing, and developing ScholarEdge across host platforms.

---

## 1. Prerequisites

- **Python**: 3.10 to 3.12 (64-bit)
- **Node.js**: v18.0.0 or higher with `npm`
- **Git**: 2.30+
- **Hardware**: Compatible with Windows 11 AMD64 (Development Host) or Windows 11 ARM64 (Snapdragon Target).

---

## 2. Environment Setup

### Clone Repository
```powershell
git clone https://github.com/Hellinferno/Snapdragon-AI-agent-.git
cd Snapdragon-AI-agent-
```

### Backend Setup
```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install --upgrade pip
pip install -r requirements.txt
```

### Acquire ONNX Models for Embeddings and Vision
```powershell
python scripts/download_qualcomm_models.py
```
This downloads and verifies ONNX models from legitimate sources (Hugging Face, Qualcomm AI Hub) for `all-MiniLM-L6-v2` and `MobileNet-v2` in `backend/models/qualcomm/`. The LLM is `Qwen3-4B-Instruct-2507` in QAIRT / GenAI Inference Extensions format, not an ONNX/QNN artifact.

### Run Automated Backend Tests
```powershell
pytest -v
```
All 119 offline test cases run without network access or API keys (about 10–15 seconds warm, which includes a nested pytest collection run by the documentation guard below; the first run after a cold boot is slower, and a few ONNX-dependent tests skip when the local model files have not been downloaded).

Two separate guards keep the documentation itself honest:
```powershell
python -m scripts.check_docs   # fails if any doc's test count or cited result file is stale
pytest tests/test_doc_consistency.py
```
If you add or remove tests, `check_docs` fails until the documented count is updated — that is intentional, and it is how four contradictory counts (95 / 79 / 37 / 31) accumulated unnoticed before.

### Start Backend Development Server
```powershell
uvicorn app.main:app --reload --port 8000
```
- API Swagger Documentation: `http://localhost:8000/docs`
- Health & Runtime Telemetry: `http://localhost:8000/api/health`

---

## 3. Frontend Setup

### Install Dependencies & Build
```powershell
cd ../frontend
npm install
npm run build
```

### Launch Vite Development Server
```powershell
npm run dev
```
Open `http://localhost:5173` in your browser.

---

## 4. Key Developer Principles

1. **Strict Source Grounding**: Never generate cross-paper claims or answers without retrieved, verifiable evidence.
2. **Explicit Refusal**: If evidence similarity is below threshold or documents lack the requested information, return an explicit refusal rather than guessing.
3. **Truthful Telemetry**: Never display `Hexagon NPU Active` unless the relevant runtime is physically executing: `QNNExecutionProvider` for embeddings/vision, or a validated QAIRT session for the LLM.
4. **Memory Safety**: Keep process memory under 500 MB RSS on development laptops to prevent out-of-memory errors on 8 GB systems.
