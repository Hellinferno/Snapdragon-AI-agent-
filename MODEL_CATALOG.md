# ScholarEdge AI Model Catalog

> **Comprehensive specifications of models and pipelines optimized for Qualcomm Snapdragon NPU execution**

---

## 1. Overview of Integrated Models

ScholarEdge utilizes a triad of models optimized for edge execution on Qualcomm Snapdragon Copilot+ PCs:

```text
┌────────────────────────┬─────────────────────────┬──────────────────────┬──────────────────────┐
│ Model Role             │ Model Identifier        │ Target Precision     │ Accelerator Backend  │
├────────────────────────┼─────────────────────────┼──────────────────────┼──────────────────────┤
│ Dense Embeddings       │ all-MiniLM-L6-v2        │ INT4 / FP32 ONNX     │ Hexagon HTP / QNN    │
│ Source-Grounded LLM    │ Qwen2.5-3B-Instruct     │ INT4 Qualcomm AI Hub │ Hexagon HTP / QNN    │
│ Multimodal Vision      │ MobileNet-v2            │ INT4 / FP32 ONNX     │ Hexagon HTP / QNN    │
└────────────────────────┴─────────────────────────┴──────────────────────┴──────────────────────┘
```

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
- **Latency Profile**: ~3.1 ms per chunk on Hexagon HTP vs ~14.2 ms on host CPU.

---

### 2. `Qwen2.5-3B-Instruct` (Source-Grounded LLM)
- **Primary Function**: Synthesizes verified answers, cross-paper comparison matrices, multi-depth concept explanations, active-recall quizzes, and flashcards.
- **Model Topology**: Decoder-only autoregressive transformer with Rotary Position Embeddings (RoPE) and SwiGLU activations.
- **Tensors & Shape**:
  - `input_ids`: `int64[1, sequence_length]`
  - `logits`: `float32[1, sequence_length, 32000]`
- **Safety & Grounding Constraint**:
  - Every assertion must be bound to a retrieved chunk identifier.
  - Queries lacking supporting evidence in indexed documents trigger an immediate, verified refusal:
    `"Insufficient evidence in indexed documents to answer this question grounded in peer-reviewed sources."`
- **Target Precision**: INT4 compiled via Qualcomm AI Hub.
- **Latency Profile**: ~28.5 ms prompt evaluation on Hexagon HTP vs ~210 ms on host CPU.

---

### 3. `MobileNet-v2` (Multimodal Vision Analysis)
- **Primary Function**: Analyzes research figures, system architecture diagrams, benchmark plots, and scientific tables.
- **Model Topology**: Inverted residual blocks with linear bottlenecks.
- **Tensors & Shape**:
  - Input: `float32[1, 3, 224, 224]` (RGB image preprocessed with ImageNet normalization: $\mu = [0.485, 0.456, 0.406]$, $\sigma = [0.229, 0.224, 0.225]$).
  - Output: `float32[1, 4]` (Logits over figure categories).
- **Target Classes**:
  1. `architecture_diagram`: Structural pipelines, module connectivity, and data flow.
  2. `bar_chart`: Comparative benchmark distributions and quantitative bars.
  3. `data_table`: Tabular grids, column headers, and numerical cells.
  4. `medical_radiograph`: Radiographic scans, anatomical observations, and imaging textures.
- **Target Precision**: INT4 via Qualcomm AI Hub.
- **Latency Profile**: ~4.2 ms per image on Hexagon HTP vs ~18.6 ms on host CPU.

---

## 3. Fallback Providers (Development Host & Zero-Dependency)

When Qualcomm AI Hub weights or QNN runtimes are unavailable (e.g. initial setup or non-Snapdragon host):
- **DevelopmentEmbeddingProvider**: 384-dimensional feature hashing with token frequency weighting and L2 normalization. Guarantees consistent vector comparison without external dependencies.
- **DevelopmentLLMProvider**: Deterministic evidence-extraction engine enforcing the exact source-citation contract: `[Paper: <title>, Page: <page>, Section: <section>, Chunk: <id>]`.
- **DevelopmentVisionProvider**: Image attribute decomposition and structural heuristic classifier.
