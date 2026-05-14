# Builder Agents

Builder Agents are Veklom-internal workers that turn public market pain into original, sellable marketplace tools. They are not customer features and they do not ship in buyer packages.

## Objective

Create a clean-room production line for high-value hybrid tools:

- MCP servers
- SDKs
- CLIs
- CI/CD actions
- agent workflows
- deployment packs
- connector packages
- audit and compliance packs

The revenue outcome is a defensible marketplace inventory of original tools that solve real developer and operator problems.

## Operators

| Worker | Role | Output |
|---|---|---|
| `builder-scout` | Finds public pain signals from compliant sources. | Opportunity records with source lineage and no copied code. |
| `builder-forge` | Builds approved original tools. | Tested package, docs, install flow, and marketplace metadata. |
| `builder-arbiter` | Enforces provenance, license, safety, and release gates. | Approval, rejection, or remediation record. |

These workers are registered in `/api/v1/internal/operators/workers` and write audit evidence through `/api/v1/internal/operators/runs`.

## Allowed Sources

- GitHub issue metadata, discussions, releases, and public API search results.
- Official documentation, changelogs, package registries, and security advisories.
- Public forums where automated access is allowed by policy or API terms.
- Vendor status pages and support articles.

## Forbidden Sources

- Private repositories, private forums, leaked files, copied proprietary code, or bypassed access controls.
- Repackaging another repo as a Veklom product.
- Copying implementation structure when license or authorship is unclear.
- Publishing a marketplace tool without provenance and release-gate evidence.

## Execution Flow

1. `builder-scout` captures public problem signals and normalizes them into an opportunity brief.
2. UACP scores the opportunity for legality, originality, revenue value, technical feasibility, and buyer urgency.
3. `builder-arbiter` rejects unsafe or duplicate opportunities before implementation.
4. `builder-forge` builds an original Veklom-native tool from the approved spec.
5. Tests, install checks, secret scans, license checks, and docs checks run before release.
6. `builder-arbiter` records release-gate evidence.
7. Approved tools enter marketplace review.

## Opportunity Record

```json
{
  "opportunity_id": "builder_YYYYMMDD_slug",
  "category": "mcp|sdk|cli|cicd|connector|agent_workflow|deployment_pack|audit_pack",
  "problem_statement": "The specific buyer pain being solved.",
  "buyer": "developer|operator|regulated_team|marketplace_vendor",
  "source_lineage": [
    {
      "source_type": "github_issue|forum|docs|registry|status_page|advisory",
      "url": "https://example.com/public-source",
      "captured_at": "2026-05-07T00:00:00Z",
      "allowed_access": true,
      "notes": "Public signal only. No code copied."
    }
  ],
  "uacp_score": {
    "revenue_value": 0,
    "buyer_urgency": 0,
    "technical_feasibility": 0,
    "legal_safety": 0,
    "originality": 0
  },
  "clean_room_rules": [
    "Do not copy third-party code.",
    "Design from observed problem pattern only.",
    "Build original interfaces, tests, docs, and package layout."
  ],
  "release_gates": {
    "license_review": "pending",
    "secret_scan": "pending",
    "tests": "pending",
    "install_check": "pending",
    "marketplace_metadata": "pending"
  }
}
```

## Upstash Box Experiment

Box is the private operator workstation layer for running Builder Agent experiments. It must not hold owner keys or production admin credentials.

Initial setup:

- Use QStash only for readiness heartbeat until the Box worker is reviewed.
- Enable the heartbeat with `ENABLE_BUILDER_AGENT_QSTASH=true`.
- Provide `INTERNAL_OPERATOR_TOKEN` as a superuser-owned automation key.
- Keep research jobs read-only until UACP and `builder-arbiter` approve the build lane.

Heartbeat endpoint:

```text
POST /api/v1/internal/operators/workers/builder-scout/heartbeat
```

Run evidence endpoint:

```text
POST /api/v1/internal/operators/runs
```

Required run evidence:

- public source list
- access method
- no-copy statement
- UACP decision
- license review state
- build/release gate state
- operator action required, if any

## Failure Rules

- If a source has unclear access rights, mark the opportunity `blocked`.
- If license review is incomplete, do not build a marketplace package.
- If tests or install checks fail, do not publish.
- If provenance is incomplete, do not publish.
- If an agent cannot prove clean-room implementation, delete the generated package and keep only the audit record.

