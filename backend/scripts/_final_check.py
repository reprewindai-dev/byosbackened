"""Final deploy verification."""
import time
import httpx

print("Waiting 120s for Cloudflare Pages deploy...")
for i in range(24):
    time.sleep(5)
    print(f"  {(i+1)*5}s...")

print("\n=== CI Status ===")
r = httpx.get(
    "https://api.github.com/repos/reprewindai-dev/byosbackened/actions/runs",
    params={"per_page": 5, "branch": "main"},
    timeout=15,
)
for run in r.json().get("workflow_runs", []):
    print(f"  {run['name']}: {run['status']} ({run['conclusion'] or 'running'})")

print("\n=== veklom.com workspace check ===")
r2 = httpx.get("https://veklom.com/overview", timeout=15, follow_redirects=True)
import re
js_refs = re.findall(r'index-[A-Za-z0-9_-]+\.js', r2.text)
css_refs = re.findall(r'index-[A-Za-z0-9_-]+\.css', r2.text)
print(f"  JS: {js_refs}")
print(f"  CSS: {css_refs}")
if "index-EUKZeqk4" in r2.text:
    print("  >>> CORRECT BUILD DEPLOYED <<<")
else:
    print(f"  Not yet updated (may still be propagating)")

print("\n=== Asset check ===")
r3 = httpx.get("https://veklom.com/workspace-assets/index-EUKZeqk4.js", timeout=15, follow_redirects=True)
ct = r3.headers.get("content-type", "")
is_js = "javascript" in ct
print(f"  JS asset: {r3.status_code}, type={ct}, is_js={is_js}, size={len(r3.content)}")
