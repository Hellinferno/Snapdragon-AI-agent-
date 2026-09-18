# ScholarEdge Benchmark Methodology

> **Status: no physical Snapdragon NPU benchmark has been recorded for the current Qwen3-4B-Instruct-2507 QAIRT integration.**

## Current validation state

| Component | Target runtime | Current state |
|---|---|---|
| all-MiniLM-L6-v2 embeddings | ONNX Runtime + QNN | Provider and benchmark harness are present; current-target physical results must be captured before being published. |
| Qwen3-4B-Instruct-2507 LLM | GenAI Inference Extensions / QAIRT | Bundle detection and tokenizer loading are implemented; inference, physical NPU validation, and benchmarks are pending. |
| MobileNet-v2 vision | ONNX Runtime + QNN | Provider and benchmark harness are present; current-target physical results must be captured before being published. |

No latency, throughput, power, memory, target-profile, or “VERIFIED” performance values are published here. Earlier ONNX/QNN LLM measurements and projections do not describe the current LLM path and have been removed.

## Reproducible benchmark protocol

Run the benchmark only on the target Windows-on-ARM Snapdragon host after the relevant runtime has been installed and the application reports physical execution for the component under test.

```powershell
cd backend
python scripts/benchmark_snapdragon.py
```

For every recorded run, retain the generated JSON artifact and record:

- device model, OS build, architecture, runtime versions, and provider/runtime actually selected;
- model artifact identifier and precision;
- cold and warm latency distribution, throughput, and memory methodology;
- whether the result came from QNN (embedding/vision) or QAIRT / GenAI Inference Extensions (LLM);
- the command, input corpus, iteration count, and timestamp needed to reproduce it.

Do not infer LLM NPU execution from `QNNExecutionProvider`: Qwen3 uses QAIRT, not ONNX Runtime. Do not label a result verified until the generated artifact confirms execution on a physical Snapdragon device and the corresponding runtime reports active hardware use.

## Publication rule

Add benchmark numbers only after QAIRT generation is implemented and the target-device run succeeds. Until then, the correct LLM status is **integration scaffolded; physical validation pending**.
