import { cpSync, existsSync, mkdirSync, readdirSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const workspaceRoot = resolve(here, "..");
const repoRoot = resolve(workspaceRoot, "..", "..");
const distRoot = resolve(workspaceRoot, "dist");
const landingRoot = resolve(repoRoot, "backend", "landing");
const assetSource = resolve(distRoot, "workspace-assets");
const assetTarget = resolve(landingRoot, "workspace-assets");
const workspaceShell = resolve(landingRoot, "workspace-app.html");
const assetVersion = process.env.WORKSPACE_ASSET_VERSION || "workspace";

const routeShells = [
  "control-center",
  "dashboard",
  "uacp",
  "playground",
  "marketplace",
  "models",
  "pipelines",
  "deployments",
  "monitoring",
  "vault",
  "compliance",
  "billing",
  "team",
  "settings",
];

if (!existsSync(resolve(distRoot, "index.html"))) {
  throw new Error("dist/index.html is missing. Run npm run build first.");
}

if (!existsSync(assetSource)) {
  throw new Error("dist/workspace-assets is missing. Check vite.config.ts assetsDir.");
}

rmSync(assetTarget, { recursive: true, force: true });
mkdirSync(assetTarget, { recursive: true });
cpSync(assetSource, assetTarget, { recursive: true });

const normalizedShell = readFileSync(resolve(distRoot, "index.html"), "utf8")
  .replace(/(\/workspace-assets\/[^"']+\.(?:js|css))(?!\?)/g, `$1?v=${assetVersion}`)
  .replace(/\r/g, "")
  .split("\n")
  .map((line) => line.trimEnd())
  .join("\n")
  .trimEnd() + "\n";

writeFileSync(workspaceShell, normalizedShell, "utf8");

for (const route of routeShells) {
  const targetDir = resolve(landingRoot, route);
  mkdirSync(targetDir, { recursive: true });
  writeFileSync(resolve(targetDir, "index.html"), normalizedShell, "utf8");
}

const assets = readdirSync(assetTarget);
console.log(`Exported Veklom Workspace shell to ${workspaceShell}`);
console.log(`Exported ${assets.length} workspace asset(s) to ${assetTarget}`);
