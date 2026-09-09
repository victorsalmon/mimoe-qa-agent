# Local QA report

Run: 2026-09-09T23:35:38.537516+00:00

PASS: 4 | FAIL: 2 | ERROR: 0

Assertions determine outcomes. AI notes are unverified drafts for human review.

Model: smollm-360m

Bodies are limited to 4,000 characters. No follow-up tests suggested by AI were executed.

## Check 1: PASS

    ID: health
    Service reports healthy
    Reproduce: GET /health
    Expected HTTP: 200
    Expected JSON fields: {"status": "ok"}
    Actual HTTP: 200
    Duration: 31.35 ms

### Assertion evidence

    All assertions passed.

### Response body

    {"status": "ok"}

## Check 2: PASS

    ID: existing-item
    Existing item returns its catalog details
    Reproduce: GET /items/1
    Expected HTTP: 200
    Expected JSON fields: {"id": 1, "name": "Notebook", "price": 5}
    Actual HTTP: 200
    Duration: 20.5 ms

### Assertion evidence

    All assertions passed.

### Response body

    {"id": 1, "name": "Notebook", "price": 5}

## Check 3: FAIL

    ID: missing-item
    Missing item must return HTTP 404
    Reproduce: GET /items/999
    Expected HTTP: 404
    Expected JSON fields: {"error": "Item not found"}
    Actual HTTP: 200
    Duration: 21.11 ms

### Assertion evidence

    Expected HTTP 404; received HTTP 200.

### Response body

    {"error": "Item not found"}

### Bug draft — derived from assertions

    Title: Missing item must return HTTP 404
    Steps: Send GET /items/999; compare the response with the expected contract above.
    Observed: Expected HTTP 404; received HTTP 200.
    Root cause and severity: not established by these checks.

### AI draft — unverified

    The observed API bug is a missing item in the list. The expected HTTP 404 response is received, but the actual response is HTTP 200. This suggests that the missing item is not present in the list.

    To follow-up the test, we can use the following steps:

    1. Check the list of missing items:
    ```
    assert missing_items == ['item1', 'item2', 'item3']
    ```
    2. Check the actual response:
    ```
    assert response == 'HTTP 200'
    ```
    3
    [Model output reached the token limit and may be incomplete.]

## Check 4: PASS

    ID: valid-quote
    Two items cost ten units
    Reproduce: GET /quote?quantity=2
    Expected HTTP: 200
    Expected JSON fields: {"quantity": 2, "total": 10}
    Actual HTTP: 200
    Duration: 22.03 ms

### Assertion evidence

    All assertions passed.

### Response body

    {"quantity": 2, "total": 10}

## Check 5: FAIL

    ID: negative-quantity
    Negative quantity must return HTTP 400
    Reproduce: GET /quote?quantity=-1
    Expected HTTP: 400
    Expected JSON fields: {"error": "Quantity must be nonnegative"}
    Actual HTTP: 200
    Duration: 20.54 ms

### Assertion evidence

    Expected HTTP 400; received HTTP 200.
    Missing JSON field 'error'.

### Response body

    {"quantity": -1, "total": -5}

### Bug draft — derived from assertions

    Title: Negative quantity must return HTTP 400
    Steps: Send GET /quote?quantity=-1; compare the response with the expected contract above.
    Observed: Expected HTTP 400; received HTTP 200. Missing JSON field 'error'.
    Root cause and severity: not established by these checks.

### AI draft — unverified

    The observed API bug in this case is that the `get` method of the `quote` object does not return a `400` status code. Instead, it returns a `200` status code. This is because the `get` method of the `quote` object is not implemented in the `get` method of the `quote` object.

    To fix this bug, you can add the following line to your code:

    ```javascript
    get("quote", -1, "invalid")
    ```

    This line will return a `2
    [Model output reached the token limit and may be incomplete.]

## Check 6: PASS

    ID: invalid-quantity
    Non-numeric quantity is rejected
    Reproduce: GET /quote?quantity=abc
    Expected HTTP: 400
    Expected JSON fields: {"error": "Quantity must be an integer"}
    Actual HTTP: 400
    Duration: 20.41 ms

### Assertion evidence

    All assertions passed.

### Response body

    {"error": "Quantity must be an integer"}
