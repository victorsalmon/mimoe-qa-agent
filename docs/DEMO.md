# Three-minute interview walkthrough

## 1. Explain the problem (30 seconds)

“I built a local API QA agent. It runs checks, captures expected versus actual behavior, and asks a mimOE-hosted model to help describe failures. I chose Python and direct HTTP because the integration needs only a small amount of orchestration and should be easy to inspect.”

## 2. Demonstrate the connection (30 seconds)

Show the loaded model in mimOE Studio, then run:

```powershell
python -m mimoe_qa doctor
```

Explain that the base URL comes from Studio's API button. The client sends a Bearer header and an OpenAI-compatible messages array to `/chat/completions`. It uses `stream: false` to receive complete text for a report. Inference runs on the configured local device.

## 3. Find real defects (60 seconds)

```powershell
python -m mimoe_qa demo
Get-Content reports/latest/report.md
```

Point out the four passing checks and two failures:

- `/items/999`: missing item returns 200; contract expects 404.
- `/quote?quantity=-1`: negative quantity returns 200 and a negative total; contract expects a 400 error.

These are intentional defects in the fixture, not failing project tests. Show the assertion evidence and deterministic bug draft first, then the separately labeled AI draft. The demo server is automatically stopped after the run.

## 4. Explain trust and validation (60 seconds)

```powershell
python -m unittest discover -v
```

“The model cannot decide whether a check passes or change the target. Its explanations are suggestions. Live testing showed the 360M model could invent details, so the report preserves observed evidence independently. If inference is unavailable, the test results still get saved and the process reports an incomplete analysis.”

Show `agent.py` for the orchestration and `inference.py` for the small adapter. Explain the analyst protocol as the seam for fake inference in automated tests.

## Likely follow-up questions

**Why not LangChain?** The assignment accepts raw requests, and the workflow has one local testing tool and one inference adapter. A framework would add installation and abstraction without solving a current problem.

**Is this an autonomous agent?** It is a bounded workflow agent. Code controls the steps and selects failed checks for analysis; the model contributes text. It is not an open-ended model-driven planner or tool-calling loop.

**How did you use AI?** Codex assisted with code, tests, documentation, and running the local integration. The repository records real validation, including model limitations. Be ready to explain the implementation yourself and distinguish automated checks from manual review.

**What would you improve?** Evaluate a more capable local model, add deeper JSON assertions and target authentication, then measure model analysis quality against known failures. The deterministic evidence should remain authoritative.
