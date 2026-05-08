# UACP V3 Worker Registry

The runtime source of truth is `backend/apps/api/routers/internal_operators.py`.

## Protected API

```text
GET /api/v1/internal/operators/registry
```

Access is Veklom-internal only. The caller must be a superuser session or a
superuser-owned automation key with `AUTOMATION` or `ADMIN` scope.

The response includes:

- `workers`: worker identity, pillar, committees, trigger, inputs, outputs, success metric, escalation rule, rollout stage, readiness, and owned surfaces.
- `committees`: committee authority, worker membership, readiness counts, and configuration gaps.
- `minimum_live_set`: the first workers to operate before deeper autonomous builder behavior.
- `promotion_logic`: promote/demote rules and the Archives write requirement.

## Local Export

```bash
python backend/scripts/export_worker_registry.py
```

The script emits the same registry as JSON so command surfaces, docs, and
operator tools can consume the runtime model without maintaining duplicate data.

## Committees

```text
Marketplace Operations:
- herald
- harvest
- bouncer
- gauge
- arbiter

Governance & Evidence:
- ledger
- oracle
- builder-arbiter
- sheriff

Growth & Intelligence:
- signal
- scout
- mint
- welcome

Builder Systems:
- builder-scout
- builder-forge
- builder-arbiter

Experience Assurance:
- sentinel
- mirror
- polish
- glide
- pulse
- sheriff
- welcome
```

## Minimum Live Set

Start with:

- `gauge`
- `ledger`
- `sentinel`
- `mirror`
- `pulse`
- `sheriff`
- `polish`

Builder agents stay staged until QStash is intentionally enabled and
`builder-arbiter` release gates are enforced with source lineage, license
review, tests, install checks, marketplace metadata, and audit evidence.
