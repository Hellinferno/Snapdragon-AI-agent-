# ScholarEdge Demo Walkthrough

> **Step-by-step demo script for judges and reviewers**
>
> ⚠️ **This demo runs in DEVELOPMENT MODE** (Intel host, OpenRouter LLM). **SNAPDRAGON MODE**
> (on-device NPU, designed to run offline) uses **Qwen3-4B-Instruct-2507 via QAIRT / GenieX** and is
> architecturally implemented but **not physically validated**. See [LIMITATIONS.md](LIMITATIONS.md).

The journey is: **Library → Research → Compare → Learn → Vision → Runtime Inspector.**

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

1. Open `http://localhost:8000/api/health` and confirm:
   ```json
   {
     "status": "healthy",
     "provider_backend": "development",
     "active_provider": "CPUExecutionProvider",
     "hardware_npu_active": false,
     "llm_runs_locally": false,
     "external_providers_enabled": true
   }
   ```
2. In the UI, the header badge reads **`Dev Host (CPU) | Cloud LLM in use`**. Click it to open the
   **Hardware & Privacy Runtime Inspector**.

**This confirms you are evaluating the development-mode baseline. Snapdragon mode is not yet physically validated.**

---

## 📑 3. Demo Steps

### Step 1: Library
1. Open the **Library** tab and click **Load Demo Papers (1-Click)**.
2. Three synthetic papers are indexed (5 pages / 5 chunks each), plus an architecture diagram for Vision:
   - *Clinical Multimodal Transformers for Diagnostic Radiology*
   - *Privacy-Preserving On-Device Clinical Language Models*
   - *Formative Assessment and Active Recall in Medical Education*
3. Click a paper card to open the **Document Inspector**: **Extracted Chunks** shows each chunk with its
   page and section; **Raw Pages** shows the extracted page text. `Esc` closes it.
4. Delete a paper with the trash icon, then click **Load Demo Papers** again: the missing paper is
   re-indexed and the others are not duplicated.

---

### Step 2: Research (grounded RAG)
1. Open **Research (RAG)** and click the chip **Pneumonia AUC? (Direct)**:
   > *"What diagnostic accuracy and AUC did the multimodal model achieve for pneumonia detection in chest radiography?"*
2. **Expected output**: the answer reports **91.4% AUC** with the citation
   `[Doc: "Clinical Multimodal Transformers for Diagnostic Radiology", Page 4]`, and says that the paper
   does not report a separate diagnostic-accuracy figure. (The exact wording comes from the cloud LLM
   and can vary.)
3. Click **View Source Excerpt** on the page 4 evidence card. The Document Inspector opens, scrolls to
   chunk #4 (page 4, section *Key Findings*) and highlights it as the matched citation.
4. **Refusal test**: click **Pediatric dosage? (Refusal Test)**:
   > *"What is the recommended pediatric dosage of oral amoxicillin for acute otitis media in infants under two years old?"*

   The answer is *"Insufficient evidence in the indexed documents to answer this question."* with an
   **Insufficient Evidence Detected** notice — no dosage is invented.

---

### Step 3: Compare (evidence-based comparison)
1. Open **Compare**, select *Clinical Multimodal Transformers…* and *Privacy-Preserving On-Device…*,
   keep the default criteria (`diagnostic accuracy, on-device deployment`) and click **Compare Selected**.
2. **Evidence-Based Comparison** matrix: for Research Objective, Methodology, Dataset, Model /
   Architecture, Metrics, Results, Limitations and Trade-offs, each cell quotes one sentence from the
   paper with a page citation, e.g. the radiology paper's Results cell quotes *"Achieved 91.4% AUC on
   pneumonia detection…"* (Page 4 · Key Findings). Click any citation to open that exact chunk.
3. **Which paper better matches this criterion?** Each criterion shows every paper's closest passage
   with its similarity score. A paper is named only when it is clearly ahead; otherwise the verdict is
   *No clear difference*. This measures how directly a paper addresses the criterion, not which paper
   is better.
4. **Evidence gaps**: *Trade-offs* is reported as a gap for both papers — neither states an explicit
   trade-off, so nothing is filled in.

Nothing in the Compare studio is generated; it makes no LLM call.

---

### Step 4: Learn (formative assessment and retry loop)
1. Open **Learn**. In **Concept Explainer**, try Beginner, Intermediate or Deep Dive. The prompt asks the
   LLM to cite every factual sentence as `[Doc: …, Page: N]`; the studio keeps the explanation only if it
   cites at least one retrieved passage, and otherwise quotes the closest passage and labels it
   *extractive*. The prose is LLM-written, so read it against the **Supporting Evidence** cards below it.
2. Open **Interactive Quiz**: choose Easy, Medium, Hard or Research-Level. Answer a question to see the
   **Answer key**, the explanation, and the **Source** paper and page (the page the explanation cites).
   **Inspect Source Excerpt** opens that chunk. A wrong answer offers **Retry Question (Analyze Mistake)**.
3. Open **Flashcards Deck** and flip through the cards; each shows the page it was drawn from.

---

### Step 5: Vision (multimodal figure analysis)
1. Open **Vision (Figures)** and click **Open demo diagram** (available after Step 1), or upload your own
   PNG/JPEG/WebP figure.
2. **Measured on this device**: resolution, aspect ratio, colour mode, brightness, contrast, dominant
   background, colours in use, edge density, and a rule-based category (the demo diagram is a
   *Line-art figure (chart, diagram or table)*). **Confidence** reads *n/a (rule-based)*: there is no
   trained classifier, so no model confidence exists.
3. Under **Paper Context**, pick *Clinical Multimodal Transformers…*, then click
   **📄 What does the linked paper report?**. The answer says what the image analysis can and cannot
   see, then lists cited passages from the linked paper; click a cited chunk to open it.
4. Try **🔎 What kind of figure is this?** and **📐 Resolution and aspect ratio** for the measured answers.

This studio is on-device figure classification plus paper-grounded analysis. It does not read the
figure's text, values or trends, and it says so.

---

### Step 6: Hardware & Privacy Runtime Inspector
1. Click the header badge (or the status block at the bottom of the sidebar).
2. The **Runtime Inspector** shows:
   - **Active execution environment**: host, architecture, the runtime actually used for each leg
     (ONNX Runtime for embeddings, pixel statistics for vision, cloud API for the LLM), execution
     provider, and `NPU Status: Validation Pending (Host CPU)`.
   - **Local-first privacy checklist**: with OpenRouter configured, 3 checks are green (local documents,
     local embeddings, local vector search) and 3 are amber (generation is served by a cloud LLM,
     retrieved excerpts are sent to it, external providers are enabled). The badge reads
     **CLOUD LLM IN USE · NOT AIR-GAPPED**.
   - **This host vs Snapdragon target**: what runs here, the target runtime, and *No benchmark
     published* — no NPU numbers are shown before a physical run.

---

## 📊 4. RAG Benchmark Evidence

Pre-run evaluations (full mode: MiniLM ONNX vector-only retrieval + OpenRouter
`qwen/qwen-2.5-72b-instruct`, top-k = 5), re-run after the final code changes. Result files:
`backend/evaluation/results/demo_papers/final_full_k5.json` and
`backend/evaluation/results/data_science_for_business/final_full_k5.json`.

| Metric              |    409-page book |   Demo papers |
| ------------------- | ---------------: | ------------: |
| Evidence Hit@5      |    17/18 (94.4%) |  13/13 (100%) |
| Page Hit@5          |     18/18 (100%) |  13/13 (100%) |
| Answer correctness  |    17/18 (94.4%) | 12/13 (92.3%) |
| False refusals      | 1/18 (5.6%, B14) |          0/13 |
| Abstention accuracy |       2/2 (100%) |    2/2 (100%) |
| Groundedness        |    16/17 (94.1%) |  13/13 (100%) |

> Evaluation performed on the development laptop with the same settings as the frozen baseline.
> Qualcomm NPU execution was not available on this machine.

**Known gaps**: one cross-document demo question misses a second paper's keyword; on the book, the
multi-hop question B14 is refused because its Chapter 11 evidence is never retrieved, and in this run
B12 was answered correctly but without a citation (it cited correctly in 3 of 3 isolated re-runs).
Details: [BENCHMARKS.md](BENCHMARKS.md#rag-quality-development-host).

To re-run: `cd backend && python -m evaluation.run_eval --dataset demo_papers --mode full --label rerun`
(for the book corpus, add `--dataset data_science_for_business --corpus-dir ..`).

---

## 🎯 5. What Judges Should Look For

| Feature | Demo verification (development mode) | Snapdragon status |
|---|---|---|
| **Grounded RAG with page citations** | ✅ Works | 🎯 Target (QAIRT generation not yet implemented) |
| **Evidence-based comparison** | ✅ Works (extractive, no LLM) | 🎯 Target |
| **Formative learning loop** | ✅ Works | 🎯 Target |
| **Figure analysis + paper context** | ✅ Works (pixel statistics, no neural model) | 🎯 Target (no trained figure classifier yet) |
| **Air-gapped privacy** | ❌ Development mode uses OpenRouter | 🎯 Designed for it; not yet tested |
| **On-device NPU inference** | ❌ Development mode uses the CPU | 🎯 Pending physical validation |
| **Verified Snapdragon benchmarks** | ❌ Not yet run | 🎯 Pending physical validation |

**Honest framing**: "The complete five-studio application works end to end on an Intel development
host, with grounded RAG, evidence-based comparison, formative learning and figure analysis. The
providers are isolated behind a factory so the same application targets Snapdragon — MiniLM through
ONNX Runtime + QNN and Qwen3 through QAIRT / GenieX. Physical Snapdragon validation is the remaining
milestone; see LIMITATIONS.md and SNAPDRAGON.md."

---

## 🧪 6. Automated Test Suite (Hermetic)

```powershell
cd backend
pytest -v
```

- **125 hermetic tests**: 0 API keys, 0 network. Every provider is forced to a local deterministic
  implementation, regardless of your `.env`. On a host without the Qualcomm ONNX/QAIRT artifacts, 7 of
  them skip because the artifact they exercise is absent.
- **Optional live integration tests** (separate; require an OpenRouter API key and internet):

```powershell
$env:RUN_LIVE_TESTS = "1"
$env:OPENROUTER_API_KEY = "sk-..."
pytest -m integration
```
