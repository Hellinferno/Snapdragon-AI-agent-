# ScholarEdge — Vibe Coding Protocol

This file defines how AI coding assistants should work on ScholarEdge.

## Before coding

The agent must:
1. read `AGENTS.md`;
2. read the relevant specification in `docs/`;
3. inspect the existing implementation;
4. identify the smallest change that satisfies the task;
5. avoid implementing unrelated roadmap items.

## During coding

The agent should:
- preserve existing interfaces;
- prefer composition over duplicated logic;
- write clear types/schemas;
- add tests for behavior;
- keep provider-specific code isolated;
- handle expected errors;
- avoid speculative abstractions.

## AI-specific rules

Never:
- invent sources;
- fabricate benchmark results;
- claim NPU acceleration without evidence;
- silently fall back from grounded retrieval to unsupported general knowledge;
- expose API keys;
- send documents to external services without explicit configuration.

## RAG changes

Any change touching retrieval must verify:
- page metadata;
- document identity;
- chunk identity;
- source propagation;
- empty retrieval behavior.

## UI changes

Any new screen/feature must define:
- loading state;
- empty state;
- error state;
- success state;
- source/evidence state where relevant.

## Snapdragon changes

Any Snapdragon-specific PR should document:
- device;
- OS;
- model;
- model version;
- runtime;
- precision;
- execution provider;
- benchmark method;
- observed results.

## Completion response

When finishing a task, report:
1. what changed;
2. tests run;
3. test results;
4. known limitations;
5. next logical task.

Never say "complete" when tests or required verification are missing.
