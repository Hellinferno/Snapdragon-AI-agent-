# ScholarEdge Benchmark Methodology

> **Status: no physical Snapdragon NPU benchmark has been recorded for the current Qwen3-4B-Instruct-2507 QAIRT integration.**

## RAG quality (development host)

Final full-mode run after the last code changes (2026-09-19): MiniLM ONNX embeddings, vector-only
retrieval, top-k = 5, evidence threshold 0.08, generation by OpenRouter `qwen/qwen-2.5-72b-instruct`.
Result files: `backend/evaluation/results/data_science_for_business/final_full_k5.json` and
`backend/evaluation/results/demo_papers/final_full_k5.json`. These numbers describe the
retrieval-and-grounding pipeline on the Intel development host. They are
not Snapdragon measurements.

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

Additional metrics from the same run:

| Metric | 409-page book | Demo papers |
|---|---|---|
| Questions | 18 answerable + 2 unanswerable | 13 answerable + 2 unanswerable |
| Doc Hit@5 | 18/18 (100%) | 13/13 (100%) |
| Page recall@5 | 0.812 | 0.923 |
| MRR | 0.681 | 0.821 |
| Citation faithfulness | 30/30 (100%) | 35/35 (100%) |
| Search P50 / P95 | 770 ms / 1,367 ms | 25 ms / 112 ms |

**Run log, reported as measured.** The first full book run (2026-09-19) crashed at question B02:
OpenRouter's upstream provider returned HTTP 429 (rate limited) and the fallback provider it routed
to rejected the request with HTTP 400. `run_eval` has no retry, so that run produced no result. The
same command was re-run unchanged once the rate limit cleared, and the table reports that complete
run. B12 was then re-run three times in isolation only to diagnose its missing citation (it cited
correctly each time); those diagnostic runs did not replace the recorded result. No run was
repeated to obtain a better number.

What changed against the frozen baseline (`head_full_k5.json`, `p1b_minilm.json`):

- **Retrieval is identical** (same evidence hit, page recall and MRR on both corpora), as expected:
  the final code changes touched section labels, prompts, comparison and vision, not ranking.
- **Answer correctness, false refusals and abstention are unchanged.** The only failing book question
  is still B14 (a multi-hop question whose Chapter 11 evidence is never retrieved), refused rather than
  answered wrongly.
- **Book groundedness is 16/17 instead of 17/17**: B12 was answered correctly but without a citation
  in this run. Three isolated re-runs of B12 with the same code cited correctly each time, so this is
  run-to-run variance of the cloud LLM, which is exactly why a single run is reported as measured
  rather than rounded up.
- Search latency on the book is the SQLite full vector scan over ~1,900 chunks on an i3-1215U; it
  varies with machine load between runs.

Reproduce (the book PDF is not redistributed; put it in the repo root):

```bash
cd backend
python -m evaluation.run_eval --dataset demo_papers --mode full --embedding-provider onnx_minilm --no-hybrid --label final_full_k5
python -m evaluation.run_eval --dataset data_science_for_business --corpus-dir .. --mode full --embedding-provider onnx_minilm --no-hybrid --label final_full_k5
```

Configuration comparisons (feature hashing vs MiniLM, BM25 fusion, top-k sweep) are in
[LIMITATIONS.md §5](LIMITATIONS.md#5-rag-quality-measured-on-development-host) and
`backend/evaluation/README.md`.

## Snapdragon validation state

| Component | Target runtime | Current state |
|---|---|---|
| all-MiniLM-L6-v2 embeddings | ONNX Runtime + QNN | Provider and benchmark harness are present; current-target physical results must be captured before being published. |
| Qwen3-4B-Instruct-2507 LLM | GenAI Inference Extensions / QAIRT | Bundle detection and tokenizer loading are implemented; inference, physical NPU validation, and benchmarks are pending. |
| MobileNet-v2 vision | ONNX Runtime + QNN | Scaffolding only: no figure classifier has been trained, so there is nothing to benchmark yet. Figure analysis currently runs as pixel statistics on the CPU. |

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
