"""Production smoke checks for the current Veklom public/workspace experience.

This script intentionally checks only safe public endpoints unless
VEKLOM_SMOKE_ACCESS_TOKEN is supplied. With a token it also verifies tenant-
scoped workspace state, wallet, models, GitHub repos, and authenticated
playground protection.
"""
from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


SITE_BASE = os.getenv("VEKLOM_SMOKE_SITE_BASE", "https://veklom.com").rstrip("/")
API_BASE = os.getenv("VEKLOM_SMOKE_API_BASE", "https://api.veklom.com/api/v1").rstrip("/")
ACCESS_TOKEN = os.getenv("VEKLOM_SMOKE_ACCESS_TOKEN")
RUN_AI = os.getenv("VEKLOM_SMOKE_RUN_AI") == "1"


@dataclass
class Check:
    name: str
    ok: bool
    detail: str


def _request(url: str, *, method: str = "GET", token: str | None = None, body: dict | None = None) -> tuple[int, str]:
    data = None
    headers = {"User-Agent": "veklom-production-smoke/1.0"}
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = Request(url, data=data, headers=headers, method=method)
    try:
        with urlopen(req, timeout=20) as resp:
            return resp.status, resp.read().decode("utf-8", errors="replace")
    except HTTPError as exc:
        return exc.code, exc.read().decode("utf-8", errors="replace")
    except URLError as exc:
        return 0, str(exc)


def check_page(path: str, expected: str) -> Check:
    status, text = _request(f"{SITE_BASE}{path}")
    return Check(f"page {path}", status == 200 and expected in text, f"status={status}")


def check_json(path: str, expected_status: int = 200, token: str | None = None) -> Check:
    status, text = _request(f"{API_BASE}{path}", token=token)
    ok = status == expected_status
    detail = f"status={status}"
    if ok and text:
        try:
            data = json.loads(text)
            if isinstance(data, dict):
                detail += f" keys={','.join(list(data)[:6])}"
            elif isinstance(data, list):
                detail += f" count={len(data)}"
        except json.JSONDecodeError:
            ok = False
            detail += " invalid_json"
    return Check(f"api {path}", ok, detail)


def main() -> int:
    checks = [
        check_page("/", "Watch AI get governed"),
        check_page("/dashboard/", "/workspace-live.js"),
        check_page("/playground/", "/workspace-live.js"),
        check_page("/marketplace/", "/workspace-live.js"),
        check_page("/marketplace/github-actions-checkout/", "/workspace-live.js"),
        check_json("/marketplace/listings"),
        check_json("/marketplace/categories"),
        check_json("/marketplace/listings/github-actions-checkout"),
        check_json("/auth/github/login"),
        check_json("/edge/canary/public"),
    ]

    status, _ = _request(
        f"{API_BASE}/ai/complete",
        method="POST",
        body={"model": "ollama-default", "prompt": "smoke", "max_tokens": 1},
    )
    checks.append(Check("playground unauthenticated is protected", status == 401, f"status={status}"))

    if ACCESS_TOKEN:
        checks.extend(
            [
                check_json("/auth/me", token=ACCESS_TOKEN),
                check_json("/workspace/overview", token=ACCESS_TOKEN),
                check_json("/workspace/models", token=ACCESS_TOKEN),
                check_json("/workspace/api-keys", token=ACCESS_TOKEN),
                check_json("/wallet/balance", token=ACCESS_TOKEN),
                check_json("/subscriptions/current", token=ACCESS_TOKEN),
            ]
        )
        repo_status, repo_text = _request(f"{API_BASE}/auth/github/repos", token=ACCESS_TOKEN)
        checks.append(Check("github repos authenticated", repo_status in (200, 400), f"status={repo_status} {repo_text[:120]}"))
        if RUN_AI:
            status, text = _request(
                f"{API_BASE}/ai/complete",
                method="POST",
                token=ACCESS_TOKEN,
                body={
                    "model": "ollama-default",
                    "prompt": "Reply with one short sentence confirming the playground is live.",
                    "max_tokens": 16,
                },
            )
            ok = status == 200
            detail = f"status={status}"
            if ok:
                data = json.loads(text)
                detail += f" model={data.get('model')} tokens={data.get('output_tokens')} wallet={data.get('wallet_balance')}"
            else:
                detail += f" {text[:160]}"
            checks.append(Check("playground authenticated AI call", ok, detail))
    else:
        checks.append(Check("authenticated tenant checks", True, "skipped: set VEKLOM_SMOKE_ACCESS_TOKEN"))

    failed = [check for check in checks if not check.ok]
    for check in checks:
        print(f"{'PASS' if check.ok else 'FAIL'} {check.name}: {check.detail}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
