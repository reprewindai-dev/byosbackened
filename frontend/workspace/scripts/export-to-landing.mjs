import { existsSync, readdirSync, readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

// ---------------------------------------------------------------------------
// The accepted production workspace artifact is FROZEN.
//
// workspace-app.html  → references index-EUKZeqk4.js + index-WqgIFi2m.css
// workspace-assets/   → contains the frozen JS + CSS bundles
//
// This script now VALIDATES the freeze instead of overwriting it.
// If you need to ship a new build, update the FROZEN_* constants below
// in the same commit as the new assets.
// ---------------------------------------------------------------------------

const FROZEN_JS = "index-EUKZeqk4.js";
const FROZEN_CSS = "index-WqgIFi2m.css";

const here = dirname(fileURLToPath(import.meta.url));
const workspaceRoot = resolve(here, "..");
const repoRoot = resolve(workspaceRoot, "..", "..");
const landingRoot = resolve(repoRoot, "backend", "landing");
const assetTarget = resolve(landingRoot, "workspace-assets");
const workspaceShell = resolve(landingRoot, "workspace-app.html");

// Verify the frozen assets are present
const jsPath = resolve(assetTarget, FROZEN_JS);
const cssPath = resolve(assetTarget, FROZEN_CSS);

if (!existsSync(jsPath)) {
  throw new Error(
    `Frozen workspace JS missing: ${FROZEN_JS}\n` +
    `Restore it with: git checkout be84be06 -- backend/landing/workspace-assets/${FROZEN_JS}`
  );
}
if (!existsSync(cssPath)) {
  throw new Error(
    `Frozen workspace CSS missing: ${FROZEN_CSS}\n` +
    `Restore it with: git checkout be84be06 -- backend/landing/workspace-assets/${FROZEN_CSS}`
  );
}

// Verify workspace-app.html references the frozen bundle
const shellContent = readFileSync(workspaceShell, "utf8");
if (!shellContent.includes(FROZEN_JS)) {
  throw new Error(
    `workspace-app.html does not reference ${FROZEN_JS}.\n` +
    `The accepted artifact has been tampered with.`
  );
}
if (!shellContent.includes(FROZEN_CSS)) {
  throw new Error(
    `workspace-app.html does not reference ${FROZEN_CSS}.\n` +
    `The accepted artifact has been tampered with.`
  );
}

const assets = readdirSync(assetTarget);
console.log(`Workspace artifact freeze verified: ${FROZEN_JS} + ${FROZEN_CSS}`);
console.log(`${assets.length} asset(s) in ${assetTarget}`);
