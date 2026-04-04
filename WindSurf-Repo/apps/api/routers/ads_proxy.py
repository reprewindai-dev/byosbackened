"""ExoClick NeverBlock server-side ad proxy.

Proxies requests to ExoClick's syndication servers so ads
are served from the site's own domain, bypassing adblockers.
"""

import httpx
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse

router = APIRouter(prefix="/ads", tags=["ads"])

EXOCLICK_API = "https://syndication-adblock.exoclick.com/ads-multi.php"
EXOCLICK_API_VERSION = "1"


@router.get("/exoclick")
async def proxy_exoclick_ads(request: Request, zones: str = ""):
    """
    Proxy ExoClick NeverBlock API calls server-side.

    Query params:
      zones  — comma-separated zone IDs, e.g. ?zones=123456,654321
    """
    if not zones:
        raise HTTPException(status_code=400, detail="zones parameter required")

    zone_ids = [z.strip() for z in zones.split(",") if z.strip()]
    if not zone_ids:
        raise HTTPException(status_code=400, detail="No valid zone IDs provided")

    # Build query params for multi-zone request
    params: dict = {"v": EXOCLICK_API_VERSION}
    for i, zone_id in enumerate(zone_ids):
        params[f"zones[{i}][idzone]"] = zone_id

    # Forward the real visitor IP
    client_ip = (
        request.headers.get("X-Forwarded-For", "").split(",")[0].strip()
        or request.client.host
        or "1.1.1.1"
    )
    params["user_ip"] = client_ip

    headers = {
        "X-Forwarded-For": client_ip,
        "Referer": str(request.headers.get("Referer", "https://veklom.dev")),
        "User-Agent": request.headers.get("User-Agent", ""),
        "Accept-Language": request.headers.get("Accept-Language", "en-US,en;q=0.9"),
    }

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(EXOCLICK_API, params=params, headers=headers)
            resp.raise_for_status()
            data = resp.json()
    except httpx.TimeoutException:
        return JSONResponse(content={"zones": []}, status_code=200)
    except Exception:
        return JSONResponse(content={"zones": []}, status_code=200)

    return JSONResponse(content=data)
