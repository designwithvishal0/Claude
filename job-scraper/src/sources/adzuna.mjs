// Adzuna: free self-serve API (https://developer.adzuna.com). Aggregates listings
// from thousands of boards/company sites across many countries, India included.
const RESULTS_PER_PAGE = 50;

export const name = "adzuna";

export function isConfigured(env) {
  return Boolean(env.ADZUNA_APP_ID && env.ADZUNA_APP_KEY);
}

export async function fetchJobs({ env, queries, countries, maxAgeHours }) {
  const appId = env.ADZUNA_APP_ID;
  const appKey = env.ADZUNA_APP_KEY;
  const maxDaysOld = Math.max(1, Math.ceil(maxAgeHours / 24));

  const jobs = [];
  for (const country of countries) {
    for (const query of queries) {
      const url = new URL(`https://api.adzuna.com/v1/api/jobs/${country}/search/1`);
      url.searchParams.set("app_id", appId);
      url.searchParams.set("app_key", appKey);
      url.searchParams.set("results_per_page", String(RESULTS_PER_PAGE));
      url.searchParams.set("what", query);
      url.searchParams.set("max_days_old", String(maxDaysOld));
      url.searchParams.set("sort_by", "date");
      url.searchParams.set("content-type", "application/json");

      const res = await fetch(url);
      if (!res.ok) {
        console.warn(`[adzuna] ${country}/"${query}" failed: ${res.status} ${res.statusText}`);
        continue;
      }
      const body = await res.json();
      for (const r of body.results ?? []) {
        jobs.push({
          id: `adzuna:${r.id}`,
          source: "Adzuna",
          title: r.title?.trim(),
          company: r.company?.display_name?.trim() ?? "Unknown",
          location: r.location?.display_name ?? country.toUpperCase(),
          url: r.redirect_url,
          postedAt: r.created,
          remote: /remote/i.test(r.title ?? "") || /remote/i.test(r.location?.display_name ?? ""),
          salary: r.salary_min && r.salary_max ? `${Math.round(r.salary_min)}-${Math.round(r.salary_max)}` : null,
          description: (r.description ?? "").slice(0, 280),
          query,
          country,
        });
      }
    }
  }
  return jobs;
}
