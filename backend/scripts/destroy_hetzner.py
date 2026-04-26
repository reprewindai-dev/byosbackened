"""
Veklom — Hetzner panic-button.

Deletes Veklom-tagged Hetzner resources.

  python scripts/destroy_hetzner.py                  # delete ALL projects (panic)
  python scripts/destroy_hetzner.py --project yacobi # delete only the yacobi server
  python scripts/destroy_hetzner.py --yes            # skip confirm (CI-safe)

What gets deleted:
  • Servers labeled project=<name>  (or all projects if --project omitted)
  • Matching firewalls
  • SSH key 'veklom-deploy' (only when ALL projects are torn down)

Hetzner billing stops within ~1 hour of server deletion. Backups are
released immediately.

USE THIS IF:
  - You panic about cost
  - One project is dead and you want to stop paying for its server
  - The credit-card owner asks you to stop spending
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Reuse the HetznerClient + load_env from setup_hetzner.py
sys.path.insert(0, str(Path(__file__).resolve().parent))
from setup_hetzner import (  # type: ignore
    HetznerClient, load_env,
    GREEN, RED, YELLOW, CYAN, BOLD, END,
    ok, fail, info, warn, head,
)


def main() -> int:
    ap = argparse.ArgumentParser(description="Delete Veklom-managed Hetzner resources")
    ap.add_argument("--project", default=None,
                    help="Only tear down this project (e.g. veklom or yacobi). "
                         "Omit to tear down ALL projects.")
    ap.add_argument("--yes", action="store_true", help="Skip confirmation prompt")
    args = ap.parse_args()

    head("Veklom · Hetzner PANIC button")

    env = load_env()
    token = env.get("HETZNER_API_TOKEN", "")
    if not token:
        fail("HETZNER_API_TOKEN missing in .env.hetzner")
        return 2

    client = HetznerClient(token)

    # Inventory: filter by project if requested, else by managed_by label
    project = args.project.strip().lower() if args.project else None

    if project:
        # Only this project's resources
        servers = client.get(f"/servers?label_selector=project={project}").get("servers", [])
        fws = [f for f in client.get("/firewalls").get("firewalls", [])
               if (f.get("labels") or {}).get("project") == project]
        keys = []  # SSH key is shared; only delete on full teardown
    else:
        # ALL managed resources
        servers = client.get("/servers?label_selector=managed_by=setup_hetzner.py").get("servers", [])
        # Fall back to project-labeled servers if managed_by isn't on existing ones
        if not servers:
            all_servers = client.get("/servers").get("servers", [])
            servers = [s for s in all_servers if (s.get("labels") or {}).get("project") in {"veklom", "yacobi"}]
        all_fws = client.get("/firewalls").get("firewalls", [])
        fws = [f for f in all_fws
               if (f.get("labels") or {}).get("project") in {"veklom", "yacobi"}
               or f.get("name") in {"veklom-prod-fw", "yacobi-prod-fw"}]
        keys = [k for k in client.get("/ssh_keys").get("ssh_keys", [])
                if k.get("name") == "veklom-deploy"]

    print(f"\n{BOLD}Found:{END}")
    for s in servers:
        ip = (s.get("public_net") or {}).get("ipv4", {}).get("ip", "?")
        print(f"  • Server  {s['name']:<25} {ip}  status={s['status']}")
    for f in fws:
        print(f"  • Firewall {f['name']:<25} id={f['id']}")
    for k in keys:
        print(f"  • SSH key {k['name']:<25} id={k['id']}")

    if not (servers or fws or keys):
        ok("Nothing to delete. Account is already clean.")
        return 0

    if not args.yes:
        scope = f"project '{project}'" if project else "ALL Veklom-managed projects"
        confirm_token = f"destroy {project}" if project else "destroy all"
        print(f"\n{RED}{BOLD}This will DELETE {scope}.{END}")
        print(f"{YELLOW}Hetzner billing for the servers stops within 1 hour.{END}")
        print(f"{YELLOW}Snapshots/backups are released immediately.{END}")
        ans = input(f"\nType '{confirm_token}' to confirm: ").strip().lower()
        if ans != confirm_token:
            info("Cancelled. Nothing deleted.")
            return 1

    head("Deleting")
    failures = 0

    for s in servers:
        try:
            client.delete(f"/servers/{s['id']}")
            ok(f"deleted server {s['name']} (id={s['id']})")
        except Exception as e:
            fail(f"could not delete server {s['name']}: {e}")
            failures += 1

    for f in fws:
        try:
            client.delete(f"/firewalls/{f['id']}")
            ok(f"deleted firewall {f['name']} (id={f['id']})")
        except Exception as e:
            fail(f"could not delete firewall {f['name']}: {e}")
            failures += 1

    for k in keys:
        try:
            client.delete(f"/ssh_keys/{k['id']}")
            ok(f"deleted ssh key {k['name']} (id={k['id']})")
        except Exception as e:
            fail(f"could not delete ssh key {k['name']}: {e}")
            failures += 1

    head("Result")
    if failures == 0:
        print(f"{GREEN}{BOLD}All Veklom-tagged Hetzner resources are gone.{END}")
        print(f"{CYAN}Billing for the servers will stop within ~1 hour.{END}")
        print(f"{CYAN}Confirm at https://console.hetzner.cloud → Billing.{END}")
        return 0
    print(f"{RED}{failures} item(s) failed to delete. Check Hetzner Console manually.{END}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
