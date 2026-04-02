export const runtime = "nodejs";

export async function GET() {
  return Response.json({
    ok: true,
    service: "ai-router-dragdrop",
    ts: new Date().toISOString(),
  });
}
