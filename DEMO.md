# ScholarEdge Evaluation & Demo Walkthrough

> **Step-by-Step Demonstration Script for Judges and Reviewers**
>
> ⚠️ **IMPORTANT**: This demo runs in **DEVELOPMENT MODE** (Intel host, OpenRouter LLM). The **SNAPDRAGON MODE** (fully air-gapped, on-device NPU) uses **Qwen3-4B-Instruct-2507 via GenieX/QAIRT** and is architecturally implemented but **not physically validated**. See [LIMITATIONS.md](LIMITATIONS.md) for the complete disclosure.

---

## 🚀 1. Launching the Application

### Start Backend
```powershell
cd backend
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --port 8000
```

### Start Frontend
```powershell
cd frontend
npm run dev
```

Open `http://localhost:5173` in your browser.

---

## 📋 2. Mode Verification (Do This First)

Before evaluating features, verify the execution mode:

1. Open `http://localhost:8000/api/health` — confirm:
   ```json
   {
     "status": "healthy",
     "provider_backend": "development",
     "external_providers_enabled": true,
     "hardware_provider": "CPUExecutionProvider",
     "hardware_npu_active": false
   }
   ```
2. In the UI, click the **Execution Badge** (top-right) — it should show:
   ```
   Host: Windows AMD64 | Provider: CPUExecutionProvider | Status: Development Host
   ```

**This confirms you are evaluating the Development Mode baseline. Snapdragon Mode is not yet physically validated.**

---

## 📑 3. Demo Evaluation Steps

### Step 1: 1-Click Seed Demo Papers
1. Navigate to the **Document Library** (Tab 1).
2. Click the green button **"Load Demo Papers (1-Click)"**.
3. Three peer-reviewed-style papers and an architecture figure are ingested:
   - *Clinical Multimodal Transformers for Diagnostic Radiology*
   - *Privacy-Preserving On-Device Clinical Language Models*
   - *Formative Assessment and Active Recall in Medical Education*

---

### Step 2: Grounded Research Studio (RAG)
1. Click on the **Research Mode** tab.
2. Click the evaluation prompt chip:
   > *"What diagnostic accuracy and AUC did the multimodal model achieve for pneumonia detection in chest radiography?"*
3. **Inspect Output**:
   - The model answers: `"The model achieved 91.4% AUC."` with citation `[Clinical Multimodal Transformers, p.4, Section: Results, Chunk: #1]`.
   - Click **"View Source Excerpt"** on the citation card. The Document Inspector modal opens, jumps to the Chunks tab, and highlights the exact matching chunk in glowing emerald.
4. Test the **Grounded Refusal Guarantee**:
   - Click the prompt chip: *"What is the recommended pediatric dosage of oral amoxicillin for acute otitis media in infants under two years old?"*
   - **Inspect Output**: The system strictly refuses:
     > `"Insufficient evidence in indexed documents to answer this question grounded in peer-reviewed sources."`
     > It does not fabricate or hallucinate medical dosages.

---

### Step 3: Compare Studio (Cross-Paper Synthesis & Recommendations)
1. Switch to the **Compare Mode** tab.
2. Ensure both paper 1 and paper 2 are selected, then click **"Synthesize Comparison"**.
3. **Inspect Output**:
   - **Narrative Cross-Paper Synthesis**: Details commonalities, methodological differences, performance differences, dataset differences, limitations, and contradictory findings.
   - **Decision Recommendations ("Which Paper is Stronger for X?")**:
     - *Diagnostic Accuracy & Multimodal Performance*: Clinical Multimodal Transformers (91.4% AUC).
     - *On-Device Edge Privacy & PHI Compliance*: Privacy-Preserving Clinical Language Models.
   - **Side-by-Side Matrix**: Full comparative grid with per-cell source references.

---

### Step 4: Learning Studio (Formative Assessment & Mistake Retry Loop)
1. Switch to the **Learn Mode** tab.
2. Under **Concept Explainer**, explore *Beginner*, *Intermediate*, or *Deep-Dive* pedagogical levels.
3. Switch to the **Interactive Quiz** subtab:
   - Notice the **4-Tier Difficulty Selector**: `Easy`, `Medium`, `Hard`, `Research-Level`.
   - Select an answer option. The system provides instant feedback with:
     - Verified finding and correct answer.
     - Pedagogical explanation.
     - Verifiable source document and page number.
     - **"Inspect Source Excerpt"** button.
     - If incorrect, a red **"Retry Question (Analyze Mistake)"** button appears to facilitate the active recall learning loop.
4. Switch to **Flashcards Deck** and flip through active-recall cards.

---

### Step 5: Multimodal Vision Studio (Figure Analysis)
1. Switch to the **Vision (Figures)** tab.
2. Click on the pre-loaded architecture diagram or upload your own research plot.
3. **Decomposition Card**:
   - Visual telemetry: Resolution, Aspect Ratio, Format, and Confidence score.
   - Figure classification: Categorized via MobileNet-v2 ONNX.
4. **Researcher Quick Prompts**:
   - Click **"📊 What does this graph show?"**
   - Click **"🔄 Explain the pipeline"**
   - Click **"🔢 Extract the important numbers"**
   - Click **"🔬 Describe observable structures"** (returns visual observations, not clinical diagnoses).

---

### Step 6: Hardware & Privacy Runtime Inspector
1. In the top right header or the bottom of the left sidebar, click the **Execution Badge**:
   > `Host: Windows AMD64 | Provider: CPUExecutionProvider`
2. The **ScholarEdge Hardware & Privacy Runtime Inspector Modal** opens:
   - **Active Environment**: Displays Host Machine, Architecture, Engine, Provider, and truthful NPU status (`Validation Pending`).
   - **Demonstrable Privacy Checklist**: 6 checks — Development Mode shows 4 green (local storage, embeddings, search, no uploads) and 2 yellow (cloud LLM via OpenRouter, external providers enabled).
   - **CPU vs Snapdragon NPU Benchmark Comparison Table**: Displays physically measured host CPU latencies alongside **target** (not verified) Snapdragon Hexagon NPU profiles.

---

## 📊 4. RAG Benchmark Evidence (Pre-Run)

The repository includes a pre-run RAG evaluation on the "Data Science for Business" corpus:

**Location**: `backend/evaluation/results/data_science_for_business/baseline.json`

**Key Measured Metrics (Development Host)**:
| Metric | Value |
|---|---|
| Doc Hit@K | 100% |
| Page Hit@K | 66.7% |
| Evidence Hit@K | 50% |
| Answer Correctness | 44.4% |
| False Refusal Rate | 44.4% |
| Abstention Accuracy | 100% |
| Groundedness | 100% |
| Citation Accuracy | 100% |
| Search Latency (P50) | 263 ms |
| Chat Latency (P50) | 2,742 ms |

**Known Gaps**: Multi-page questions (33% evidence hit), Cross-section (33%), Conceptual (40%), Page citations (66%).

To re-run: `cd backend && python -m evaluation.run_eval --dataset data_science_for_business --corpus-dir .. --mode full --label rerun`

---

## 🎯 5. What Judges Should Look For

| Feature | Demo Verification | Competition Claim |
|---|---|---|
| **Grounded RAG with page citations** | ✅ Works in Dev Mode | ✅ Architecture ready for Snapdragon |
| **Cross-paper comparison** | ✅ Works in Dev Mode | ✅ Architecture ready for Snapdragon |
| **Formative learning loop** | ✅ Works in Dev Mode | ✅ Architecture ready for Snapdragon |
| **Vision figure analysis** | ✅ Works in Dev Mode | ✅ Architecture ready for Snapdragon |
| **Air-gapped privacy** | ❌ Dev Mode uses OpenRouter | 🎯 **Snapdragon Mode target** |
| **On-device NPU inference** | ❌ Dev Mode uses CPU | 🎯 **Snapdragon Mode target** |
| **Verified Snapdragon benchmarks** | ❌ Not yet run | 🎯 **Pending physical validation** |

**Honest framing for judges**: "We've built the complete 5-studio application with grounded RAG, cross-paper synthesis, formative learning, and vision analysis. The architecture is fully isolated behind a provider factory so the *same application* can run on Intel (development) or Snapdragon NPU (target). Physical Snapdragon validation is the remaining milestone — see LIMITATIONS.md and SNAPDRAGON.md for the exact checklist."