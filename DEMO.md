# ScholarEdge Evaluation & Demo Walkthrough

> **Step-by-Step Demonstration Script for Judges and Reviewers**

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

## 📑 2. Demo Evaluation Steps

### Step 1: 1-Click Seed Demo Papers
1. Navigate to the **Document Library** (Tab 1).
2. Click the green button **"Load Demo Papers (1-Click)"**.
3. Three peer-reviewed-style papers and an architecture figure are ingested with zero external downloads:
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
   - **Demonstrable Privacy Checklist**: 6 green checkmarks verifying local storage, local embeddings, local search, local inference, zero uploads, and external providers disabled.
   - **CPU vs Snapdragon NPU Benchmark Comparison Table**: Displays physically measured host CPU latencies alongside target Snapdragon Hexagon NPU profiles.
