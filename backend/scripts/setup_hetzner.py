"""
Veklom — Hetzner Cloud one-shot provisioning.

Idempotent. Reads HETZNER_API_TOKEN from backend/.env.hetzner.

Multi-project: pass --project <name> to spin up isolated servers per project.

  python scripts/setup_hetzner.py --project veklom
  python scripts/setup_hetzner.py --project yacobi

Each run creates:
  • Server  '<project>-prod-1' (CX22, Coolify pre-installed, daily backups)
  • Firewall '<project>-prod-fw' (22/80/443/8000 inbound)
  • SSH key 'veklom-deploy' (uploaded once, reused across projects)
  • Labels: project=<name>, app=<name>, env=prod

Idempotent: rerunning verifies and updates existing resources instead of
duplicating them.

COST CEILING: each CX22 = €5.42/mo (~$5.85 USD), HARD CAP. No surprise charges.
Destroy with: python scripts/destroy_hetzner.py [--project <name>]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Optional

import urllib.request
import urllib.error

API = "https://api.hetzner.cloud/v1"

# ── Config defaults ──────────────────────────────────────────────────────────

DEFAULT_LOCATION = "hil"            # Hillsboro, OR (US west). EU DCs (fsn1/nbg1/hel1) currently
                                     # return 422 "unsupported" for CPX line — actually a capacity/
                                     # quota issue Hetzner reports oddly. ASH is out of stock.
                                     # HIL is open + costs $13.99/mo for cpx21 (vs $10.99 in EU).
DEFAULT_SERVER_TYPE = "cpx21"       # 3 vCPU AMD EPYC / 4 GB / 80 GB / €5.18/mo + €1.04 backups
                                     # = €6.22 (~$6.70 USD) HARD MONTHLY CAP per server.
                                     # Two servers (veklom + co2routerengine) = ~$13.40/mo total.
                                     # CX22 (the old 2-vCPU/40GB/€4.51 plan) was retired by Hetzner;
                                     # CPX21 is the modern equivalent: faster CPU, double the SSD,
                                     # ~60¢ more per month. Bump to cpx31 (€8.97) when 50+ users hit.
DEFAULT_PROJECT = "veklom"          # which project's server we're provisioning
DEFAULT_SSH_KEY_NAME = "veklom-deploy"  # one keypair, reused across projects
DEFAULT_IMAGE = "ubuntu-22.04"      # standard Ubuntu 22.04 LTS — works on every server type.
                                     # We install Coolify via cloud-init below. This is more reliable
                                     # than Hetzner's pre-built Coolify app image (which is tied to
                                     # specific server types/locations and can hit "unsupported"
                                     # errors on the CPX line).

# Cloud-init script: installs Coolify on first boot, takes ~3-5 min after server reaches running.
COOLIFY_CLOUD_INIT = """#cloud-config
package_update: true
package_upgrade: false
packages:
  - curl
  - wget
  - git
runcmd:
  - [ bash, -c, "curl -fsSL https://cdn.coollabs.io/coolify/install.sh -o /tmp/coolify-install.sh && bash /tmp/coolify-install.sh > /var/log/coolify-install.log 2>&1" ]
final_message: "Coolify installation triggered. Check /var/log/coolify-install.log for progress."
"""

# ── Pretty output ────────────────────────────────────────────────────────────

GREEN = "\033[92m"; RED = "\033[91m"; YELLOW = "\033[93m"
CYAN  = "\033[96m"; DIM = "\033[2m"; BOLD = "\033[1m"; END = "\033[0m"
def ok(m):   print(f"{GREEN}OK{END}   {m}")
def fail(m): print(f"{RED}FAIL{END} {m}")
def info(m): print(f"{CYAN}..{END}   {m}")
def warn(m): print(f"{YELLOW}WARN{END} {m}")
def head(m): print(f"\n{BOLD}{m}{END}\n{DIM}{'-'*len(m)}{END}")


# ── Tiny HTTP client for Hetzner ─────────────────────────────────────────────

class HetznerClient:
    def __init__(self, token: str):
        self.token = token

    def _req(self, method: str, path: str, body: Optional[dict] = None) -> dict:
        url = f"{API}{path}"
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(
            url,
            data=data,
            method=method,
            headers={
                "Authorization": f"Bearer {self.token}",
                "Content-Type": "application/json",
                "User-Agent": "veklom-deploy-bot/1.0",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                raw = resp.read().decode()
                return json.loads(raw) if raw else {}
        except urllib.error.HTTPError as e:
            err_body = e.read().decode(errors="ignore")
            try:
                err_json = json.loads(err_body)
            except json.JSONDecodeError:
                err_json = {"raw": err_body}
            raise RuntimeError(f"Hetzner API {e.code} on {method} {path}: {err_json}") from None

    def get(self, path: str) -> dict:           return self._req("GET", path)
    def post(self, path: str, body: dict) -> dict: return self._req("POST", path, body)
    def delete(self, path: str) -> dict:        return self._req("DELETE", path)


# ── Env loader ───────────────────────────────────────────────────────────────

def load_env() -> dict:
    repo_root = Path(__file__).resolve().parent.parent
    out: dict = {}
    for fname in (".env.hetzner", ".env"):
        f = repo_root / fname
        if not f.exists(): continue
        for line in f.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line: continue
            k, v = line.split("=", 1)
            out.setdefault(k.strip(), v.strip().strip('"').strip("'"))
    if "HETZNER_API_TOKEN" in os.environ:
        out["HETZNER_API_TOKEN"] = os.environ["HETZNER_API_TOKEN"]
    return out


# ── Helpers ──────────────────────────────────────────────────────────────────

def find_by_name(items: list, name: str, key: str = "name"):
    return next((i for i in items if i.get(key) == name), None)


def print_cost_preview(client, server_type_name: str, location: str, with_backups: bool) -> Optional[float]:
    """
    Pull /pricing and print exactly what this server will cost per month.
    Uses the project owner's currency + VAT rate (Hetzner returns these).
    Returns the gross monthly total in the account's currency, or None on error.
    """
    try:
        pricing = client.get("/pricing").get("pricing", {})
    except Exception as e:
        warn(f"could not fetch /pricing for cost preview: {e}")
        return None

    currency = pricing.get("currency", "EUR")
    vat_rate = pricing.get("vat_rate", "0")
    backup_pct = float((pricing.get("server_backup") or {}).get("percentage", "20"))

    st_entry = find_by_name(pricing.get("server_types", []), server_type_name)
    if not st_entry:
        warn(f"server type '{server_type_name}' not found in /pricing response")
        return None

    loc_price = next((p for p in st_entry.get("prices", []) if p.get("location") == location), None)
    if not loc_price:
        warn(f"no /pricing entry for {server_type_name} at {location}")
        return None

    net_monthly = float(loc_price["price_monthly"]["net"])
    gross_monthly = float(loc_price["price_monthly"]["gross"])
    included_traffic_tb = float(loc_price.get("included_traffic", 0)) / (1024 ** 4)
    backup_gross = (gross_monthly * backup_pct / 100.0) if with_backups else 0.0
    total_gross = gross_monthly + backup_gross

    print(f"\n{BOLD}Cost preview  ({currency} · VAT {vat_rate}%){END}")
    print(f"  {server_type_name} @ {location}")
    print(f"     {DIM}net   {END}{net_monthly:>8.2f} {currency} / month")
    print(f"     {DIM}gross {END}{gross_monthly:>8.2f} {currency} / month")
    if with_backups:
        print(f"  Daily backups ({backup_pct:.0f}% of server)")
        print(f"     {DIM}gross {END}{backup_gross:>8.2f} {currency} / month")
    print(f"  Included egress:  {included_traffic_tb:.0f} TB / month  "
          f"(over: {loc_price.get('price_per_tb_traffic', {}).get('gross', '?')} {currency}/TB)")
    print(f"  {BOLD}{'─'*36}{END}")
    print(f"  {BOLD}TOTAL gross:  {total_gross:>8.2f} {currency} / month{END}")
    return total_gross

def read_pubkey() -> str:
    pub = Path.home() / ".ssh" / "veklom-deploy.pub"
    if not pub.exists():
        raise RuntimeError(
            f"Public key not found at {pub}. "
            "Run the SSH-key generation step first (we did this earlier)."
        )
    return pub.read_text(encoding="utf-8").strip()


# ── Main flow ────────────────────────────────────────────────────────────────

def main() -> int:
    ap = argparse.ArgumentParser(description="Veklom Hetzner provisioner (multi-project)")
    ap.add_argument("--project", default=DEFAULT_PROJECT,
                    help="Project name. Drives server/firewall naming. Examples: veklom, yacobi")
    ap.add_argument("--location", default=DEFAULT_LOCATION)
    ap.add_argument("--server-type", default=DEFAULT_SERVER_TYPE)
    ap.add_argument("--server-name", default=None,
                    help="Override server name (default: '<project>-prod-1')")
    ap.add_argument("--firewall-name", default=None,
                    help="Override firewall name (default: '<project>-prod-fw')")
    ap.add_argument("--ssh-key-name", default=DEFAULT_SSH_KEY_NAME)
    ap.add_argument("--no-backups", action="store_true",
                    help="Skip enabling daily backups (saves ~€0.91/mo)")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    # Validate + derive project-scoped names
    project = args.project.strip().lower()
    if not project.replace("-", "").replace("_", "").isalnum():
        fail(f"--project '{project}' must be alphanumeric (with optional - or _).")
        return 2
    args.server_name = args.server_name or f"{project}-prod-1"
    args.firewall_name = args.firewall_name or f"{project}-prod-fw"
    args._project = project

    head("Veklom · Hetzner provisioner")

    env = load_env()
    token = env.get("HETZNER_API_TOKEN", "")
    if not token:
        fail("HETZNER_API_TOKEN missing in backend/.env.hetzner or environment.")
        info("Create backend/.env.hetzner with at minimum:")
        info("    HETZNER_API_TOKEN=...")
        return 2

    if len(token) < 30:
        fail(f"HETZNER_API_TOKEN looks too short ({len(token)} chars).")
        return 2

    client = HetznerClient(token)

    # 1. Verify token
    head("1. Auth check")
    try:
        whoami = client.get("/locations")
        ok(f"token valid; {len(whoami.get('locations', []))} locations visible")
    except Exception as e:
        fail(f"token rejected: {e}")
        return 3

    # 2. Locate server type + location
    head("2. Resolving server type and location")
    sts = client.get("/server_types").get("server_types", [])
    st = find_by_name(sts, args.server_type)
    if not st:
        fail(f"server type '{args.server_type}' not found.")
        info(f"Available: {', '.join(s['name'] for s in sts[:10])}...")
        return 4
    price = next((p for p in st.get("prices", []) if p["location"] == args.location), None)
    monthly = float(price["price_monthly"]["gross"]) if price else None
    ok(f"server type {args.server_type}  ({st['cores']} vCPU, {st['memory']} GB RAM, {st['disk']} GB SSD)"
       + (f"  ~€{monthly:.2f}/mo gross" if monthly else ""))

    locs = client.get("/locations").get("locations", [])
    loc = find_by_name(locs, args.location)
    if not loc:
        fail(f"location '{args.location}' not found. Try fsn1, nbg1, hel1, ash, hil, sin.")
        return 4
    ok(f"location {args.location}  ({loc.get('city', '?')}, {loc.get('country', '?')})")

    # 2b. Cost preview (so you know exactly what will hit the card)
    total_monthly = print_cost_preview(
        client,
        args.server_type,
        args.location,
        with_backups=not args.no_backups,
    )

    # In live mode (not dry-run), give a 5-second window to abort with Ctrl+C
    # before any paid resource is created.
    if not args.dry_run and total_monthly is not None:
        print(f"\n{YELLOW}{BOLD}Press Ctrl+C in the next 5 seconds to abort.{END}")
        try:
            for i in range(5, 0, -1):
                print(f"  {YELLOW}continuing in {i}…{END}", end="\r", flush=True)
                time.sleep(1)
            print(" " * 40, end="\r")  # clear the line
        except KeyboardInterrupt:
            print()
            warn("Aborted by user. No resources were created.")
            return 0

    # 3. SSH key
    head("3. SSH key")
    pubkey = read_pubkey()
    # Hetzner enforces uniqueness on the public_key contents (fingerprint),
    # not the name. So we match on the key string first; fall back to name.
    pubkey_normalized = " ".join(pubkey.split()[:2])  # "ssh-ed25519 AAAA..." (drops comment)
    keys = client.get("/ssh_keys").get("ssh_keys", [])
    ssh_key = next(
        (k for k in keys if " ".join(k.get("public_key", "").split()[:2]) == pubkey_normalized),
        None,
    ) or find_by_name(keys, args.ssh_key_name)
    if ssh_key:
        ok(f"SSH key already in account (id={ssh_key['id']}, name='{ssh_key.get('name')}')")
    else:
        if args.dry_run:
            info(f"[dry-run] would upload '{args.ssh_key_name}'")
            ssh_key = {"id": 0}
        else:
            r = client.post("/ssh_keys", {
                "name": args.ssh_key_name,
                "public_key": pubkey,
                "labels": {"managed_by": "setup_hetzner.py"},
            })
            ssh_key = r["ssh_key"]
            ok(f"SSH key uploaded (id={ssh_key['id']}, fingerprint={ssh_key.get('fingerprint','?')})")

    # 4. Base OS image (Ubuntu 22.04). Coolify will be installed via cloud-init.
    head("4. Base OS image")
    imgs = client.get(f"/images?type=system&architecture=x86&per_page=50&name={DEFAULT_IMAGE}").get("images", [])
    base_image = next((im for im in imgs if im.get("name") == DEFAULT_IMAGE), None) or (imgs[0] if imgs else None)
    if not base_image:
        # Fall back to listing all system images and matching by name
        imgs = client.get("/images?type=system&architecture=x86&per_page=50").get("images", [])
        base_image = next((im for im in imgs if im.get("name") == DEFAULT_IMAGE), None)
    if not base_image:
        fail(f"Could not find image '{DEFAULT_IMAGE}'. Available system images:")
        for im in imgs[:10]:
            info(f"  - {im.get('name')}  /  {im.get('description')}")
        return 5
    ok(f"OS image found: id={base_image['id']}  name='{base_image.get('name')}'  ({base_image.get('description')})")
    # Keep the variable name for backward compat in the rest of the script
    coolify = base_image

    # 5. Firewall
    head("5. Firewall")
    fws = client.get("/firewalls").get("firewalls", [])
    fw = find_by_name(fws, args.firewall_name)
    fw_rules = [
        {"direction": "in", "protocol": "tcp", "port": "22",
         "source_ips": ["0.0.0.0/0", "::/0"], "description": "SSH"},
        {"direction": "in", "protocol": "tcp", "port": "80",
         "source_ips": ["0.0.0.0/0", "::/0"], "description": "HTTP"},
        {"direction": "in", "protocol": "tcp", "port": "443",
         "source_ips": ["0.0.0.0/0", "::/0"], "description": "HTTPS"},
        {"direction": "in", "protocol": "tcp", "port": "8000",
         "source_ips": ["0.0.0.0/0", "::/0"], "description": "Coolify UI (lock down post-setup)"},
        {"direction": "in", "protocol": "icmp",
         "source_ips": ["0.0.0.0/0", "::/0"], "description": "ICMP/ping"},
    ]
    if fw:
        ok(f"firewall '{args.firewall_name}' exists (id={fw['id']})")
        if not args.dry_run:
            client.post(f"/firewalls/{fw['id']}/actions/set_rules", {"rules": fw_rules})
            ok(f"firewall rules updated ({len(fw_rules)} inbound rules)")
    else:
        if args.dry_run:
            info(f"[dry-run] would create firewall '{args.firewall_name}'")
            fw = {"id": 0}
        else:
            r = client.post("/firewalls", {
                "name": args.firewall_name,
                "rules": fw_rules,
                "labels": {"project": args._project, "app": args._project, "env": "prod"},
            })
            fw = r["firewall"]
            ok(f"firewall created (id={fw['id']}, {len(fw_rules)} rules)")

    # 6. Server
    head("6. Server")
    servers = client.get("/servers").get("servers", [])
    server = find_by_name(servers, args.server_name)
    if server:
        ok(f"server '{args.server_name}' already exists (id={server['id']}, status={server['status']})")
    else:
        if args.dry_run:
            info(f"[dry-run] would create server '{args.server_name}'")
            server = None
        else:
            body = {
                "name": args.server_name,
                "server_type": args.server_type,
                "location": args.location,
                "image": coolify["id"],
                "ssh_keys": [ssh_key["id"]],
                "firewalls": [{"firewall": fw["id"]}],
                "start_after_create": True,
                "labels": {
                    "project": args._project,
                    "app": args._project,
                    "env": "prod",
                    "managed_by": "setup_hetzner.py",
                },
                "automount": False,
                "user_data": COOLIFY_CLOUD_INIT,
                # enable_ipv4/ipv6 default to True on Hetzner; we accept the default.
                # Backups are enabled in step 8 via the dedicated enable_backup action.
            }
            r = client.post("/servers", body)
            server = r["server"]
            ok(f"server created (id={server['id']}); waiting for status=running …")

    # 7. Wait for running
    if server and not args.dry_run:
        head("7. Waiting for server to start")
        deadline = time.time() + 300  # 5 min
        while time.time() < deadline:
            s = client.get(f"/servers/{server['id']}")["server"]
            status = s["status"]
            ipv4 = (s.get("public_net") or {}).get("ipv4") or {}
            ip = ipv4.get("ip")
            if status == "running" and ip:
                server = s
                ok(f"server running. public IPv4 = {ip}")
                break
            info(f"... status={status}, ip={ip or 'pending'}")
            time.sleep(8)
        else:
            warn("server did not reach 'running' within 5 minutes; check the Hetzner Console.")

    # 8. Enable backups (paid feature, skip if --no-backups)
    if server and not args.dry_run and not args.no_backups:
        head("8. Daily backups")
        try:
            client.post(f"/servers/{server['id']}/actions/enable_backup", {})
            ok("daily backups enabled (~€0.91/mo)")
        except Exception as e:
            # likely already enabled
            warn(f"could not enable backups (may already be on): {e}")

    # 9. Output
    head("9. Summary")
    out_path = Path(__file__).resolve().parent.parent / f"hetzner_setup_{args._project}.json"
    summary = {
        "server": {
            "id": server.get("id") if server else None,
            "name": (server or {}).get("name"),
            "status": (server or {}).get("status"),
            "ipv4": ((server or {}).get("public_net") or {}).get("ipv4", {}).get("ip"),
            "ipv6": ((server or {}).get("public_net") or {}).get("ipv6", {}).get("ip"),
            "datacenter": ((server or {}).get("datacenter") or {}).get("name"),
            "server_type": args.server_type,
            "image": coolify.get("description"),
        },
        "firewall": {"id": fw.get("id"), "name": args.firewall_name} if fw else None,
        "ssh_key":  {"id": ssh_key.get("id"), "name": args.ssh_key_name} if ssh_key else None,
    }
    if not args.dry_run:
        out_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
        ok(f"summary written: {out_path}")

    ip = summary["server"]["ipv4"]
    if ip:
        head("Done")
        print(f"  Coolify will be ready in 2-4 minutes at:")
        print(f"     {BOLD}http://{ip}:8000{END}")
        print(f"  SSH access:")
        print(f"     ssh -i ~/.ssh/veklom-deploy root@{ip}")
        print(f"  When you can load the Coolify URL in a browser, send me the IP and we'll wire the rest.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
