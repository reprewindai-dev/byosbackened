# veklom.com Landing Freeze

The buyer-facing `.com` landing page is frozen at this artifact:

```text
path: backend/landing/index.html
sha256: 019bc4e1669edc412160903d8515a83c37700fe4fac0da5f8f88aeb803b5ab1d
hashing: CRLF/LF-normalized
state: Veklom Sovereign AI Hub buyer landing with GPC-first plan framing, BYOS backend CTA, and generated workspace shell routes
```

Rules:

- Do not edit `backend/landing/index.html` during `.dev`, workspace, backend, pricing, or deployment work.
- Do not copy the legacy backend demo back into `.com`.
- If `.com` must change later, update this lock and `backend/scripts/verify_com_landing_freeze.py` in the same commit with the explicit reason.
- `.dev` owns the legacy live backend demo and technical BYOS proof surface.
