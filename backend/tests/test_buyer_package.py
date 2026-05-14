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
    (root / "apps" / "api").mkdir()
    (root / "apps" / "api" / "routers").mkdir()
    (root / "apps" / "api" / "routers" / "internal_operators.py").write_text(
        "print('veklom internal only')",
        encoding="utf-8",
    )
    (root / "license").mkdir()
    (root / "license" / "__init__.py").write_text("", encoding="utf-8")
    (root / "license" / "tier.py").write_text("tier = 'starter'", encoding="utf-8")
    (root / "license" / "validator.py").write_text("print('validator')", encoding="utf-8")
    (root / "license" / "server.py").write_text("print('server')", encoding="utf-8")
    (root / "license" / "stripe_webhook.py").write_text("print('stripe')", encoding="utf-8")
    (root / "db").mkdir()
    (root / "db" / "models").mkdir()
    (root / "db" / "models" / "license_key.py").write_text("print('license key')", encoding="utf-8")
    (root / "edge").mkdir()
    (root / "edge" / "__init__.py").write_text("", encoding="utf-8")
    (root / "edge" / "router.py").write_text("print('edge')", encoding="utf-8")
    (root / "landing").mkdir()
    (root / "landing" / "index.html").write_text("marketing site", encoding="utf-8")
    (root / "acquisition").mkdir()
    (root / "acquisition" / "index.html").write_text("operator acquisition", encoding="utf-8")
    (root / "docs").mkdir()
    (root / "docs" / "notes.md").write_text("do not ship", encoding="utf-8")
    (root / "scripts").mkdir()
    (root / "scripts" / "dev_helper.py").write_text("print('dev')", encoding="utf-8")

    monkeypatch.setattr(build_buyer_package, "ROOT", root)

    out_dir = tmp_path / "out"
    zip_path = build_buyer_package.build_zip("pro", "1.2.3", out_dir)

    assert zip_path.name == "byos-ai-backend-pro-1.2.3.zip"
    assert zip_path.exists()

    with zipfile.ZipFile(zip_path) as bundle:
        names = set(bundle.namelist())

    assert "README.md" in names
    assert ".env.example" in names
    assert "docker-compose.prod.yml" in names
    assert "apps/main.py" in names
    assert "apps/api/routers/internal_operators.py" not in names
    assert "edge/router.py" in names
    assert "license/tier.py" in names
    assert "license/validator.py" in names
    assert "license/server.py" not in names
    assert "license/stripe_webhook.py" not in names
    assert "db/models/license_key.py" not in names
    assert "landing/index.html" not in names
    assert "acquisition/index.html" not in names
    assert "docs/notes.md" not in names
    assert "scripts/dev_helper.py" not in names
    assert "RELEASE_MANIFEST.json" in names
    assert "package_manifest.json" in names
    assert "package_manifest.sig" in names
    assert "license_public_key.pem" in names


def test_buyer_package_sanitizes_operator_branding(tmp_path, monkeypatch):
    root = tmp_path / "backend"
    root.mkdir()
    (root / "README.md").write_text(
        "Veklom connects to https://license.veklom.com and stores veklom-backend packages in .veklom.",
        encoding="utf-8",
    )

    monkeypatch.setattr(build_buyer_package, "ROOT", root)

    zip_path = build_buyer_package.build_zip("starter", "1.2.3", tmp_path / "out")
    with zipfile.ZipFile(zip_path) as bundle:
        readme = bundle.read("README.md").decode("utf-8")

    assert "Veklom" not in readme
    assert "license.veklom.com" not in readme
    assert "veklom-backend" not in readme
    assert ".veklom" not in readme
    assert "BYOS AI Backend" in readme
    assert "https://license.example.com" in readme
    assert "byos-ai-backend" in readme
    assert ".backend" in readme


def test_buyer_package_refuses_secret_material(tmp_path, monkeypatch):
    root = tmp_path / "backend"
    root.mkdir()
    (root / "README.md").write_text("buyer readme", encoding="utf-8")
    (root / ".env.example").write_text("SECRET_KEY=actual-secret-value", encoding="utf-8")

    monkeypatch.setattr(build_buyer_package, "ROOT", root)

    try:
        build_buyer_package.build_zip("pro", "1.2.3", tmp_path / "out")
    except RuntimeError as exc:
        assert "possible secret material" in str(exc)
    else:
        raise AssertionError("package build should refuse non-placeholder secret material")
