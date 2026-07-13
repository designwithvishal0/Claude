import { mkdir, writeFile } from "node:fs/promises";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

import * as adzuna from "./sources/adzuna.mjs";
import * as remoteok from "./sources/remoteok.mjs";
import * as twitter from "./sources/twitter.mjs";

const __dirname = dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = join(__dirname, "..", "..");
const DATA_DIR = join(REPO_ROOT, "data");

const SOURCES = [adzuna, remoteok, twitter];
const MAX_AGE_HOURS = Number(process.env.JOB_MAX_AGE_HOURS ?? 24);
const QUERIES = (process.env.JOB_QUERY ?? "software engineer,frontend developer,backend developer,product manager,data analyst")
  .split(",")
  .map((s) => s.trim())
  .filter(Boolean);
const COUNTRIES = (process.env.JOB_COUNTRIES ?? "us,gb,in,ca,au")
  .split(",")
  .map((s) => s.trim())
  .filter(Boolean);

function isFresh(job, cutoff) {
  if (!job.postedAt) return false;
  const t = new Date(job.postedAt).getTime();
  return Number.isFinite(t) && t >= cutoff;
}

function dedupeKey(job) {
  if (job.url) return job.url.split("?")[0];
  return `${job.source}:${job.title}:${job.company}`.toLowerCase();
}

async function run() {
  const cutoff = Date.now() - MAX_AGE_HOURS * 3600 * 1000;
  const results = [];

  for (const source of SOURCES) {
    if (!source.isConfigured(process.env)) {
      console.log(`[${source.name}] skipped (no credentials configured)`);
      continue;
    }
    try {
      const jobs = await source.fetchJobs({
        env: process.env,
        queries: QUERIES,
        countries: COUNTRIES,
        maxAgeHours: MAX_AGE_HOURS,
      });
      console.log(`[${source.name}] fetched ${jobs.length} listing(s)`);
      results.push(...jobs);
    } catch (err) {
      console.error(`[${source.name}] error: ${err.message}`);
    }
  }

  const fresh = results.filter((j) => isFresh(j, cutoff));
  const seen = new Set();
  const deduped = [];
  for (const job of fresh) {
    const key = dedupeKey(job);
    if (seen.has(key)) continue;
    seen.add(key);
    deduped.push(job);
  }
  deduped.sort((a, b) => new Date(b.postedAt) - new Date(a.postedAt));

  await mkdir(DATA_DIR, { recursive: true });
  await mkdir(join(DATA_DIR, "history"), { recursive: true });

  const generatedAt = new Date().toISOString();
  const payload = { generatedAt, maxAgeHours: MAX_AGE_HOURS, count: deduped.length, jobs: deduped };

  await writeFile(join(DATA_DIR, "jobs-latest.json"), JSON.stringify(payload, null, 2));
  await writeFile(
    join(DATA_DIR, "history", `jobs-${generatedAt.slice(0, 10)}.json`),
    JSON.stringify(payload, null, 2)
  );

  console.log(`Wrote ${deduped.length} fresh listing(s) (posted within ${MAX_AGE_HOURS}h) to data/jobs-latest.json`);
}

run().catch((err) => {
  console.error(err);
  process.exitCode = 1;
});
