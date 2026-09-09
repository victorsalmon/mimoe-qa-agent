# Architecture and technical decisions

## Goal and boundary

Provide an interview-sized example of connecting a real local model to a useful QA workflow. The application owns test execution and evidence. mimOE owns model hosting and inference. The model contributes advisory text after observable failures.

| Module | Responsibility |
| --- | --- |
| `cli.py` | Parse arguments, wire dependencies, select demo/custom target, map errors to exit codes |
| `config.py` | Read and validate environment settings and local URLs |
| `checks.py` | Parse test contracts; execute deterministic assertions; capture outcomes |
| `agent.py` | Execute checks, select failures, enforce inference budget, retain partial results |
| `http_client.py` | HTTP I/O, no redirects/proxies, socket timeout and response size handling |
| `inference.py` | Translate failure evidence into mimOE chat requests; validate responses |
| `reporting.py` | Write structured results and readable evidence/AI sections |
| `demo.py` | Manage the deliberately faulty temporary local API lifecycle |

Immutable dataclasses describe checks, results, settings, and reports. Their contained lists/dictionaries are treated as read-only by convention. The `Analyst` protocol is the one replaceable business boundary: a fake analyst can prove the workflow independently of model availability. A larger dependency-injection container would add complexity without helping this scope.

## Run sequence

1. Parse configuration and validate the suite before starting requests.
2. For `demo`, allocate an unused loopback port and start the fixture server.
3. Execute every check sequentially. HTTP errors remain responses so a valid 404 can pass.
4. Label mismatched assertions `FAIL`; transport or malformed JSON problems `ERROR`.
5. Select non-passing checks in suite order. Analyze up to the configured budget.
6. On inference failure, stop model calls and preserve all check evidence.
7. Stop the demo server in a `finally` block; serialize reports and return the exit code.

`doctor` is a separate diagnostic: GET `/models`, verify the configured model ID, then POST `/chat/completions`. Normal runs avoid a discovery dependency because the completion call itself is sufficient and some compatible servers expose fewer endpoints.

## Why raw HTTP

The assignment explicitly accepts raw API calls. `urllib.request`, `http.server`, `argparse`, dataclasses, and `unittest` cover the complete scope. There are no runtime framework dependencies, implicit retries, cloud defaults, or framework-specific tool-calling requirements. The tradeoff is that response validation and transport handling are our responsibility; boundary tests cover both.

## Why non-streaming

The Studio example uses `stream: true`, which produces incremental events. A report needs complete short text, so the client explicitly sends `stream: false`, a behavior verified with the installed model. This avoids maintaining an SSE parser and partial-response state. Streaming would be appropriate for a future interactive chat interface.

## Why the agent does not let the model judge tests

Small local models may hallucinate even when given correct evidence. Our live runs confirmed this. Human-authored contracts determine outcomes, and deterministic bug drafts preserve reproducibility. AI suggestions remain indented, unverified content and are never parsed as executable instructions. This design cannot guarantee factual model output; it guarantees that such output cannot silently redefine test results.

## Error semantics

- `PASS`: the expected status and requested JSON values matched.
- `FAIL`: the endpoint returned observable evidence that contradicted the contract.
- `ERROR`: a response could not be obtained or parsed as required.
- Inference errors are separate from check outcomes and make the run incomplete (exit 2).
- Budget-skipped or explicitly disabled inference is visible but not an execution error.
- An output filesystem error returns 2. Report files are ordinary local files, not a transactional store; a failed write may leave one file completed.

## Deliberate tradeoffs

- GET-only checks keep the tool understandable and avoid stateful setup/teardown.
- Sequential execution is sufficient for six demo checks and avoids saturating local inference.
- No automatic retry hides intermittent behavior or duplicates model work.
- Context is bounded by capped field lengths and response sizes; character limits are only an approximation of model token counts.
- Socket timeouts are not total run deadlines. Suite size and inference-call limits bound work count.
- The allowlist is a local-use guardrail, not a general SSRF protection library.
- Top-level JSON matching is intentionally small; schemas, JSONPath, and deep strict comparison are future extensions.

## Testing approach

Offline tests start real ephemeral HTTP servers to exercise HTTP status handling, redirects, response limits, the inference wire format, and the full CLI demo. Injected failures test transport/inference degradation and malformed protocol responses. The test suite never contacts the supplied mimOE endpoint. Live verification is a separate manual acceptance run recorded in `VALIDATION.md`.

Potential next steps: add authenticated target adapters, richer schema assertions, explicit severity rules, model-output evaluation against a curated evidence set, and a browser report viewer. These should follow concrete user needs rather than expand the assignment by default.
