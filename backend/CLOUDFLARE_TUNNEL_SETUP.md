# Cloudflare Tunnel Setup — Free Public HTTPS URL on Your Laptop

**End state:** `https://byos.yourdomain.com` (or `https://something.trycloudflare.com`) points to your laptop's API. Free forever. No credit card. Works behind any router/firewall (no port forwarding).

**Time: ~10 minutes.**

---

## Choose: with-domain or without-domain

| | Quick (no domain) | Pro (your domain) |
|---|---|---|
| **URL you get** | `https://random-words.trycloudflare.com` | `https://byos.yourdomain.com` |
| **Cost** | $0 | $0 (you provide the domain) |
| **Setup time** | 2 minutes | 10 minutes |
| **URL changes on restart?** | Yes | No |
| **Buyer-friendly?** | Fine for casual demos | Better for serious sales |

If you have any domain (cheap to grab on Porkbun, $9/yr), use Pro path. Otherwise Quick path.

---

## Quick path — `trycloudflare.com` (literally 2 commands)

### 1. Install cloudflared

```powershell
# Run in PowerShell (no admin needed)
winget install --id Cloudflare.cloudflared
```

If `winget` isn't installed, download the `.msi` from:
https://github.com/cloudflare/cloudflared/releases/latest

### 2. Start the tunnel

Make sure your API is running locally first (`start_server.ps1`).

```powershell
cloudflared tunnel --url http://localhost:8000
```

It prints:
```
Your quick Tunnel has been created! Visit it at:
https://big-pretty-words.trycloudflare.com
```

That URL is **live globally** — share it with anyone, hit it from anywhere, you get HTTPS automatically.

**Done.** Leave that terminal open. URL stays alive until you Ctrl+C.

---

## Pro path — Your own domain (named tunnel, persistent URL)

### 1. Add your domain to Cloudflare (free)

1. Buy a domain anywhere (Porkbun, Namecheap, Cloudflare itself)
2. https://dash.cloudflare.com → **Add a site** → enter your domain → free plan
3. Cloudflare gives you 2 nameservers — set them at your registrar
4. Wait 5–60 min for DNS to propagate

### 2. Install + login cloudflared

```powershell
winget install --id Cloudflare.cloudflared
cloudflared tunnel login
```

A browser opens — pick your domain, click Authorize. Cloudflare drops a cert at `%USERPROFILE%\.cloudflared\cert.pem`.

### 3. Create the tunnel

```powershell
cloudflared tunnel create byos-api
```

Outputs a tunnel UUID and creates `<UUID>.json` in `%USERPROFILE%\.cloudflared\`. **Save that UUID** — you'll need it.

### 4. Configure routing

Create `%USERPROFILE%\.cloudflared\config.yml`:

```yaml
tunnel: <PASTE-UUID-HERE>
credentials-file: C:\Users\<YOU>\.cloudflared\<UUID>.json

ingress:
  - hostname: byos.yourdomain.com
    service: http://localhost:8000
    originRequest:
      connectTimeout: 30s
      noTLSVerify: true
  - service: http_status:404
```

Replace `<UUID>`, `<YOU>`, and `byos.yourdomain.com` with real values.

### 5. Point DNS

```powershell
cloudflared tunnel route dns byos-api byos.yourdomain.com
```

This creates a CNAME automatically.

### 6. Run the tunnel

```powershell
cloudflared tunnel run byos-api
```

Visit `https://byos.yourdomain.com/health` — should return `{"status":"ok"}`.

---

## Make the tunnel auto-start at boot (Pro path only)

Run as Administrator:

```powershell
cloudflared service install
```

Now the tunnel runs as a Windows service. Survives reboots. Stops when you say:

```powershell
# Status
Get-Service cloudflared

# Stop
Stop-Service cloudflared

# Start
Start-Service cloudflared

# Uninstall
cloudflared service uninstall
```

---

## Cloudflare cache rules (massive free perf win)

In Cloudflare dashboard → your domain → **Rules → Page Rules** (or **Cache Rules** on newer UI):

| URL pattern | Setting |
|---|---|
| `byos.yourdomain.com/health` | Cache Level: Cache Everything, Edge TTL: 30 sec |
| `byos.yourdomain.com/api/v1/openapi.json` | Cache Level: Cache Everything, Edge TTL: 60 sec |
| `byos.yourdomain.com/api/v1/docs` | Cache Level: Cache Everything, Edge TTL: 5 min |
| `byos.yourdomain.com/` | Cache Level: Cache Everything, Edge TTL: 5 min |

Now those routes are served from Cloudflare's 300+ global edge locations **without ever hitting your laptop**. Buyers in Tokyo see <50ms response times. Free.

The `Cache-Control: public, s-maxage=60` header that `FastPathMiddleware` already emits is what makes Cloudflare cache. Already set up — just enable the rules.

---

## Common gotchas

**"Tunnel disconnected" in logs after laptop sleep:**
- Disable sleep: Settings → System → Power → Screen and sleep → Never (when plugged in)
- Disable hibernate: `powercfg /hibernate off` (admin PowerShell)

**API works locally but tunnel returns 502:**
- Check API is listening on `127.0.0.1:8000` not just `localhost`
- Check Windows Firewall isn't blocking cloudflared

**Want to take it offline temporarily:**
- Quick path: Ctrl+C the terminal
- Pro path: `Stop-Service cloudflared`

---

## What buyers see

- Real HTTPS URL with valid cert
- Real latency, real load handling
- Cloudflare's edge caching makes it feel like a $1000/mo deployment
- They have no idea it's your laptop. And they don't need to.

Cost so far: **$0**. With a domain: **$9/year**.
