# ScholarEdge — Snapdragon Deployment Plan

## Objective

Make ScholarEdge suitable for Snapdragon-powered Windows PCs and validate selected AI workloads on actual target hardware.

## Current status

No Snapdragon PC is currently owned by the developer.

Therefore:
- Snapdragon support is a target;
- local application development continues on an Intel ThinkBook;
- actual hardware claims require later validation.

## Intended deployment architecture

```text
ScholarEdge application
        ↓
Provider interface
        ↓
Qualcomm-compatible model/runtime
        ↓
ONNX Runtime + QNN or another verified supported path
        ↓
Snapdragon hardware
```

The exact runtime must be selected after verifying current Qualcomm documentation, model artifacts, and device compatibility.

## Qualcomm AI Hub

Use Qualcomm AI Hub to:
- identify suitable models;
- inspect supported devices;
- obtain/prepare compatible model artifacts where available;
- inspect deployment information.

Do not assume that every model in the catalog supports every runtime or device.

## Remote testing

If available to the project, use Qualcomm Device Cloud or other authorized remote Snapdragon hardware access for actual validation.

## Benchmark plan

For each selected model:
1. record model/version;
2. record runtime/version;
3. record target Snapdragon device;
4. record precision/quantization;
5. record warm/cold latency;
6. record memory;
7. record accelerator execution;
8. record application-level latency;
9. store reproducible benchmark configuration.

## Evidence requirement

A final competition claim such as "runs on Snapdragon NPU" should be supported by:
- reproducible deployment steps;
- runtime configuration;
- target device;
- benchmark/test evidence.

## Development compatibility

Do not make the entire repository require Qualcomm tooling. Snapdragon support should be an additional deployment backend.
