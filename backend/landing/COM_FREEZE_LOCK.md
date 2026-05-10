# veklom.com Landing Freeze

The buyer-facing `.com` landing page is frozen at this artifact:

```text
path: backend/landing/index.html
sha256: 42ddcc746bd6dfdcc2225693c404defece5289726355d9e91cd184a4e0834e18
hashing: CRLF/LF-normalized
state: Veklom Sovereign AI Hub with UACP black-box demo
```

Rules:

- Do not edit `backend/landing/index.html` during `.dev`, workspace, backend, pricing, or deployment work.
- Do not copy the legacy backend demo back into `.com`.
- If `.com` must change later, update this lock and `backend/scripts/verify_com_landing_freeze.py` in the same commit with the explicit reason.
- `.dev` owns the legacy live backend demo and technical BYOS proof surface.
