# veklom.com Landing Freeze

The buyer-facing `.com` landing page is frozen at this artifact:

```text
path: backend/landing/index.html
sha256: 768e51de55a7c3f82b55336399e81a83f4f5476c3c2ddb6501b071b34d5cca41
hashing: CRLF/LF-normalized
state: Veklom Sovereign AI Hub with UACP black-box demo, system-font performance path, valid robots directives
```

Rules:

- Do not edit `backend/landing/index.html` during `.dev`, workspace, backend, pricing, or deployment work.
- Do not copy the legacy backend demo back into `.com`.
- If `.com` must change later, update this lock and `backend/scripts/verify_com_landing_freeze.py` in the same commit with the explicit reason.
- `.dev` owns the legacy live backend demo and technical BYOS proof surface.
