"""Export the UACP V3 worker registry as machine-readable JSON.

The runtime registry in apps.api.routers.internal_operators is the source of
truth. This script exists so docs, command surfaces, and operator tooling can
render the same worker/committee model without maintaining a duplicate file.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from apps.api.routers.internal_operators import (  # noqa: E402
    COMMITTEE_REGISTRY,
    MINIMUM_LIVE_SET,
    WORKER_REGISTRY,
    _committee_payload,
    _worker_payload,
)


def build_registry() -> dict[str, object]:
    return {
        "version": "uacp_v3",
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "visibility": "veklom_internal_only",
        "customer_visible": False,
        "ships_to_buyer_package": False,
        "workers": [
            _worker_payload(worker_id, worker)
            for worker_id, worker in WORKER_REGISTRY.items()
        ],
        "committees": [
            _committee_payload(committee_id, committee)
            for committee_id, committee in COMMITTEE_REGISTRY.items()
        ],
        "minimum_live_set": [
            _worker_payload(worker_id, WORKER_REGISTRY[worker_id])
            for worker_id in MINIMUM_LIVE_SET
            if worker_id in WORKER_REGISTRY
        ],
        "promotion_logic": {
            "promote": "Consistently hits success metrics, produces useful outputs, and reduces founder intervention.",
            "demote": "Causes false positives, misses obvious failures, creates noise, or operates outside policy boundaries.",
            "archive_requirement": "Every promotion or demotion is written to Archives with timestamp, evidence, reason, and approving authority.",
        },
    }


def main() -> int:
    print(json.dumps(build_registry(), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
