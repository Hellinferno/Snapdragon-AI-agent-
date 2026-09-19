# ScholarEdge AI Model Catalog

> **The models ScholarEdge uses or targets, and the validation status of each**

---

## 1. Overview of Integrated Models

ScholarEdge targets two neural models on Snapdragon, plus a figure-analysis path that is not yet a neural model:

```text
┌────────────────────────┬─────────────────────────┬──────────────────────┬──────────────────────┐
│ Model Role             │ Model Identifier        │ Target Precision     │ Accelerator Backend  │
├────────────────────────┼─────────────────────────┼──────────────────────┼──────────────────────┤
│ Dense Embeddings       │ all-MiniLM-L6-v2        │ INT4 / FP32 ONNX     │ Hexagon HTP / QNN    │
│ Source-Grounded LLM    │ Qwen3-4B-Instruct-2507  │ INT4 Qualcomm AI Hub │ Hexagon HTP / QAIRT  │
│ Figure analysis        │ pixel statistics (today)│ n/a (no model)       │ CPU                  │
│                        │ MobileNet-v2 (target)   │ ONNX, not trained    │ Hexagon HTP / QNN    │
└────────────────────────┴─────────────────────────┴──────────────────────┴──────────────────────┘
```

> **Note:** The LLM uses GenAI Inference Extensions (GenieX/QAIRT) on the Hexagon NPU, distinct from the ONNX/QNN path used by the embeddings. The Qwen3 bundle is not converted to ONNX.

---

## 2. Model Specifications

### 1. `all-MiniLM-L6-v2` (Sentence Embeddings)
- **Primary Function**: Converts document text chunks and user queries into 384-dimensional dense vectors for semantic similarity search.
- **Model Topology**: 6-layer Transformer encoder with 12 self-attention heads.
- **Tensors & Shape**:
  - `input_ids`: `int64[batch_size, sequence_length]`
  - `attention_mask`: `int64[batch_size, sequence_length]`
  - `last_hidden_state`: `float32[batch_size, sequence_length, 384]`
- **Post-Processing**: Attention-masked mean pooling followed by L2 unit vector normalization:
  $$\vec{v}_{\text{norm}} = \frac{\sum_{i=1}^L m_i \cdot \vec{h}_i}{\|\sum_{i=1}^L m_i \cdot \vec{h}_i\|_2}$$
- **Target Precision**: INT4 quantized via Qualcomm AI Hub.
- **Validation Status**: ONNX/QNN is the intended Snapdragon runtime. No physical target benchmark is currently published.

---

### 2. `Qwen3-4B-Instruct-2507` (Source-Grounded LLM)
- **Primary Function**: Writes cited answers, multi-depth concept explanations, active-recall quizzes and flashcards. (The Compare studio is extractive and does not use the LLM.)
- **Model Topology**: Decoder-only autoregressive transformer with Rotary Position Embeddings (RoPE), SwiGLU activations, and Grouped Query Attention (GQA).
- **Tensors & Shape**:
  - `input_ids`: `int64[1, sequence_length]`
  - `logits`: `float32[1, sequence_length, 151936]`
- **Safety & Grounding Constraint**:
  - Every factual claim must cite a retrieved passage as `[Doc: <title>, Page: <N>]`.
  - Questions the retrieved evidence cannot answer must be refused with:
    `"Insufficient evidence in the indexed documents to answer this question."`
- **Target Precision**: INT4 compiled via Qualcomm AI Hub (QAIRT/GenieX format).
- **Runtime**: GenAI Inference Extensions (GenieX/QAIRT) on Hexagon NPU.
- **Vocabulary**: 151,936 tokens.
- **Validation Status**: Bundle detection and tokenizer loading are implemented. QAIRT inference and physical Snapdragon NPU benchmarking are pending, so no LLM latency or throughput is claimed.

---

### 3. Figure analysis (`DevelopmentVisionProvider` today; `MobileNet-v2` target)
- **What runs today**: pixel statistics measured on the CPU — resolution, aspect ratio, colour mode,
  mean brightness, contrast (luminance standard deviation), dominant background colour and share,
  colours in use, and edge density — plus a coarse category from explicit rules on those measurements
  (line-art figure; greyscale continuous-tone image; colour photograph). No neural model, no confidence
  score, and the file name plays no part in the category.
- **Target**: `QualcommVisionProvider` runs a `MobileNet-v2` ONNX session via QNN and maps its output to
  four figure classes (`architecture_diagram`, `bar_chart`, `data_table`, `medical_radiograph`).
- **Status**: scaffolding only. The public MobileNet-v2 is a 1000-class ImageNet classifier; no model has
  been trained on those four figure classes, so this path makes no classification claim and is not
  enabled in either mode.
- **Validation Status**: not validated on any hardware; no benchmark is published.

---

## 3. Fallback Providers (Development Host & Zero-Dependency)

When Qualcomm AI Hub weights or QNN runtimes are unavailable (e.g. initial setup or non-Snapdragon host):
- **DevelopmentEmbeddingProvider**: 384-dimensional feature hashing with token frequency weighting and L2 normalization. Guarantees consistent vector comparison without external dependencies, which is why it remains the zero-dependency path — but it is selected **only when the ONNX model is absent**, and it is not a semantic encoder: on the book benchmark it scores 44.4% answer correctness vector-only (72.2% with BM25 fusion) against 94.4% for ONNX MiniLM. `/api/health` therefore reports `embedding_degraded: true` whenever this provider is auto-selected, rather than letting a hash-embedding machine look like a semantic-retrieval one.
- **DevelopmentLLMProvider**: Deterministic evidence-extraction synthesizer used by the hermetic tests: it refuses when no retrieved passage overlaps the question, and otherwise quotes the top passages with their `["<title>", Page <N>, Section: "<section>"]` source headers.
- **DevelopmentVisionProvider**: Pixel-statistics figure analysis with a rule-based category (described in §3 above); it never reports a confidence score.
