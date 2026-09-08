# ScholarEdge — Claude/Coding-Agent Compatibility Instructions

Read `AGENTS.md` first. `AGENTS.md` is the canonical repository instruction file.

## Priority
Follow:
1. User requirements
2. `AGENTS.md`
3. Relevant documents in `docs/`
4. Existing code/tests
5. General engineering judgment

Do not duplicate the full project policy here. If this file conflicts with `AGENTS.md`, update this file so it points back to the canonical instructions rather than maintaining a second policy.

## Before changing code
- Identify the feature's spec.
- Inspect existing interfaces and tests.
- Keep changes minimal.
- Preserve provider abstraction.

## Before declaring completion
- Run relevant tests.
- Run the full suite when feasible.
- Verify documentation and implementation agree.
- Report limitations honestly.
