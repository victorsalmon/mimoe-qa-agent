# Validation record

Validated on 2026-09-09 on Windows with Python 3.14.6 and the user's already-running mimOE instance. The loaded model ID returned by `/models` was `smollm-360m`; its metadata reported a 2,048-token context.

## Automated verification

`python -m unittest discover -v`: **24 tests passed**.

Coverage includes the full demo with real local HTTP traffic, both intentional defects, clean runs without model calls, inference budgets, preserving evidence on model failure, transport errors, strict top-level value types, malformed JSON, invalid suites, duplicate IDs, unsafe path forms, local URL validation, invalid timeouts, redirect refusal, oversized responses, authorization/header and payload format, malformed completions, model discovery, output truncation labeling, report content isolation, and CLI report/exit behavior.

`python -m pip install .` in a fresh virtual environment successfully built and installed the wheel. The installed CLI help command succeeded. An isolated installed-package demo also verifies that the JSON fixture is packaged and can run without importing the source checkout.

The GitHub Actions workflow is configured for Windows and Ubuntu with Python 3.11 and 3.14. Local verification alone does not establish those remote matrix results; check the repository's Actions page for their current status.

## Live acceptance

The endpoint supplied through mimOE Studio was used through an environment override; no installation or model change was needed.

1. `python -m mimoe_qa doctor`: model discovery and a real non-streaming completion succeeded (exit 0).
2. `python -m mimoe_qa demo --output reports/live-validation`: **4 PASS, 2 FAIL, 0 ERROR** (expected exit 1).
3. Both failed checks received actual model text; there were no inference errors.
4. The generated Markdown and JSON were copied unchanged to `examples/live-report.md` and `examples/live-report.json`. They contain only synthetic fixture data.

Final captured live run: `2026-09-09T23:35:38.537516+00:00`. Durations and model wording may vary between runs.

## Observed model quality

Successful transport was not sufficient for trustworthy QA analysis. The 360M model invented functions, internal behavior, and suggested code. Experiments with shorter instructions and an in-context example did not reliably remove these errors. In the captured report it identifies some status-code discrepancies but still invents implementation details and reaches the output limit.

The shipped implementation therefore preserves deterministic assertions and bug drafts separately, labels AI text as unverified, and marks token-limited output as potentially incomplete. It never executes generated code or lets model output determine a test outcome. This is a documented limitation, not a claim that prompt wording solved model reliability.

## Reproduce

Follow the README quick start, using the model ID and base URL shown in your own Studio instance. Run offline tests first, then `doctor` and `demo`. A missing loaded model is an environment/inference failure; the demo's two failed assertions are the expected acceptance result.
