# Repository guidance

This is a small, local-only Python QA agent for the mimOE BYO Framework assignment.

- Run from checkout: `python -m mimoe_qa --help`.
- Offline tests: `python -m unittest discover -v`.
- Lint gate: `python -m ruff check .` (CI-enforced, 120 columns); format sources with `black` at 120 columns before committing.
- Live acceptance: set `MIMOE_BASE_URL` and `MIMOE_MODEL`, run `doctor`, then `demo`.
- Demo acceptance is 4 PASS / 2 FAIL / 0 ERROR and exit 1; two fixture defects are intentional.
- Keep test outcomes deterministic; never let model text change assertions or execute actions.
- Keep runtime dependencies empty unless a concrete requirement justifies an addition.
- Preserve module boundaries described in `docs/ARCHITECTURE.md`.
- Tests must not require live mimOE or contact external services.
- Never commit real response data or connection secrets. Only synthetic examples belong in `examples/`.
- Update README and tests when changing CLI, configuration, or report behavior.
