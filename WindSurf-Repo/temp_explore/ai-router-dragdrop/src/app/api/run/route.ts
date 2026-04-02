import { z } from "zod";
import { runRouter } from "@/lib/router";

export const runtime = "nodejs";

const BodySchema = z.object({
  appId: z.string().min(1),
  task: z.string().min(1),
  input: z.string().min(1),
  meta: z.record(z.any()).optional().default({}),
});

export async function POST(req: Request) {
  const started = Date.now();
  try {
    const bodyJson = await req.json();
    const body = BodySchema.parse(bodyJson);

    const result = await runRouter(body);
    const ms = Date.now() - started;

    return Response.json({ ...result, ms });
  } catch (err: any) {
    // Fail-OPEN: always provide usable output
    const ms = Date.now() - started;
    return Response.json({
      ok: false,
      provider: "router",
      error: err?.message ?? "Unknown error",
      output: {
        summary: "",
        score: 0,
        flags: ["ROUTER_ERROR", "AI_DOWN"],
        draft: "",
      },
      raw: null,
      ms,
    }, { status: 200 });
  }
}
