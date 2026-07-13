// RemoteOK: free, unauthenticated public JSON feed (https://remoteok.com/api).
// Their license terms require attribution + a direct (non-redirected) link back
// to the listing, both of which the viewer/data output preserve.
export const name = "remoteok";

export function isConfigured() {
  return true; // no credentials required
}

export async function fetchJobs({ queries }) {
  const res = await fetch("https://remoteok.com/api", {
    headers: { "User-Agent": "job-scraper (+https://remoteok.com/api)" },
  });
  if (!res.ok) {
    console.warn(`[remoteok] fetch failed: ${res.status} ${res.statusText}`);
    return [];
  }
  const body = await res.json();
  // First element is a legal/metadata notice, not a job.
  const rows = Array.isArray(body) ? body.filter((r) => r && r.id) : [];

  // RemoteOK tags/titles are short ("frontend", "Interface Designer"), so match on
  // individual significant words from each query rather than the full phrase.
  const wordSets = queries.map((q) =>
    q
      .toLowerCase()
      .split(/\s+/)
      .filter((w) => w.length > 3)
  );
  return rows
    .filter((r) => {
      if (wordSets.length === 0) return true;
      const haystack = `${r.position ?? ""} ${(r.tags ?? []).join(" ")}`.toLowerCase();
      return wordSets.some((words) => words.some((w) => haystack.includes(w)));
    })
    .map((r) => ({
      id: `remoteok:${r.id}`,
      source: "RemoteOK",
      title: r.position,
      company: r.company,
      location: r.location || "Remote",
      url: r.url,
      postedAt: r.date,
      remote: true,
      salary: r.salary_min && r.salary_max ? `${r.salary_min}-${r.salary_max}` : null,
      description: (r.description ?? "").replace(/<[^>]+>/g, " ").slice(0, 280),
      tags: r.tags ?? [],
    }));
}
