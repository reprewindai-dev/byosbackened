export default {
  async fetch(request: Request): Promise<Response> {
    const url = new URL(request.url);

    if (url.pathname === "/health") {
      return Response.json({
        status: "ok",
        service: "veklom-worker-sentinel",
        routes: "none",
      });
    }

    return new Response(
      "Veklom production is served by Cloudflare Pages at veklom.com and the Hetzner API at api.veklom.com.",
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
