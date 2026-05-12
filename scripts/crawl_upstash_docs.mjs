#!/usr/bin/env node
import { spawnSync } from "node:child_process";

const url = process.env.UPSTASH_SEARCH_REST_URL;
const token = process.env.UPSTASH_SEARCH_REST_TOKEN;
const index = process.env.UPSTASH_SEARCH_INDEX || "default";
const docUrl = process.argv[2] || process.env.UPSTASH_DOC_URL;

if (!url || !token || !docUrl) {
  console.error(
    "Usage: UPSTASH_SEARCH_REST_URL=... UPSTASH_SEARCH_REST_TOKEN=... UPSTASH_SEARCH_INDEX=default node scripts/crawl_upstash_docs.mjs https://example.com/docs",
  );
  process.exit(2);
}

const result = spawnSync(
  "npx",
  [
    "@upstash/search-crawler",
    "--upstash-url",
    url,
    "--upstash-token",
    token,
    "--index-name",
    index,
    "--doc-url",
    docUrl,
  ],
  {
    stdio: "inherit",
    shell: process.platform === "win32",
  },
);

process.exit(result.status ?? 1);
