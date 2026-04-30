#!/bin/sh
docker exec 1219ce7c1716 python - <<'PY'
from pathlib import Path
paths=[
'/app/apps/api/routers/marketplace_v1.py',
'/app/apps/api/main.py',
'/app/db/models/vendor.py',
'/app/db/models/__init__.py'
]
for p in paths:
    print(p, Path(p).exists())
if Path('/app/apps/api/main.py').exists():
    t=Path('/app/apps/api/main.py').read_text(errors='ignore')
    print('main_has_marketplace_v1', 'marketplace_v1' in t)
if Path('/app/db/models/vendor.py').exists():
    v=Path('/app/db/models/vendor.py').read_text(errors='ignore')
    print('vendor_has_plan', 'plan = Column' in v)
PY
