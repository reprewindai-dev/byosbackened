from __future__ import annotations

import zipfile
from pathlib import Path

from scripts import build_buyer_package


def test_buyer_package_excludes_server_only_files(tmp_path, monkeypatch):
    root = tmp_path / "backend"
    root.mkdir()

    (root / "README.md").write_text("buyer readme", encoding="utf-8")
    (root / ".env.example").write_text("EXAMPLE=1", encoding="utf-8")
    (root / "docker-compose.prod.yml").write_text("services: {}", encoding="utf-8")
    (root / "apps").mkdir()
    (root / "apps" / "main.py").write_text("print('ok')", encoding="utf-8")
    (root / "license").mkdir()
    (root / "license" / "__init__.py").write_text("", encoding="utf-8")
    (root / "license" / "tier.py").write_text("tier = 'starter'", encoding="utf-8")
    (root / "license" / "validator.py").write_text("print('validator')", encoding="utf-8")
    (root / "license" / "server.py").write_text("print('server')", encoding="utf-8")
    (root / "license" / "stripe_webhook.py").write_text("print('stripe')", encoding="utf-8")
    (root / "db").mkdir()
    (root / "db" / "models").mkdir()
    (root / "db" / "models" / "license_key.py").write_text("print('license key')", encoding="utf-8")
    (root / "docs").mkdir()
    (root / "docs" / "notes.md").write_text("do not ship", encoding="utf-8")
    (root / "scripts").mkdir()
    (root / "scripts" / "dev_helper.py").write_text("print('dev')", encoding="utf-8")

    monkeypatch.setattr(build_buyer_package, "ROOT", root)

    out_dir = tmp_path / "out"
    zip_path = build_buyer_package.build_zip("pro", "1.2.3", out_dir)

    assert zip_path.name == "veklom-backend-pro-1.2.3.zip"
    assert zip_path.exists()

    with zipfile.ZipFile(zip_path) as bundle:
        names = set(bundle.namelist())

    assert "README.md" in names
    assert ".env.example" in names
    assert "docker-compose.prod.yml" in names
    assert "apps/main.py" in names
    assert "license/tier.py" in names
    assert "license/validator.py" in names
    assert "license/server.py" not in names
    assert "license/stripe_webhook.py" not in names
    assert "db/models/license_key.py" not in names
    assert "docs/notes.md" not in names
    assert "scripts/dev_helper.py" not in names
