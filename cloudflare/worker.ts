type WorkerHealth = {
  status: "ok";
  service: "veklom-worker-sentinel";
  routes: "none";
  production: {
    public_site: "cloudflare-pages";
    api: "hetzner-coolify";
  };
};

const healthPayload: WorkerHealth = {
  status: "ok",
  service: "veklom-worker-sentinel",
  routes: "none",
  production: {
    public_site: "cloudflare-pages",
    api: "hetzner-coolify",
  },
};

export default {
  async fetch(request: Request): Promise<Response> {
    const url = new URL(request.url);

    if (url.pathname === "/health") {
      return Response.json(healthPayload, {
        headers: {
          "cache-control": "no-store",
        },
      });
    }

    return new Response(
      "Veklom production is served by Cloudflare Pages at veklom.com and the Hetzner/Coolify API at api.veklom.com. This Worker is a no-route build sentinel.",
      {
        status: 404,
        headers: {
          "content-type": "text/plain; charset=utf-8",
          "cache-control": "no-store",
        },
      },
    );
  },
};
