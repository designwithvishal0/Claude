// X/Twitter: official API v2 recent-search endpoint. Optional — the X API has no
// free tier (pay-per-use since Feb 2026), so this only runs when the caller
// supplies TWITTER_BEARER_TOKEN. Recent-search is capped to the last 7 days
// server-side; we additionally filter to maxAgeHours below.
export const name = "twitter";

export function isConfigured(env) {
  return Boolean(env.TWITTER_BEARER_TOKEN);
}

export async function fetchJobs({ env, queries, maxAgeHours }) {
  const token = env.TWITTER_BEARER_TOKEN;
  const since = new Date(Date.now() - maxAgeHours * 3600 * 1000).toISOString();
  const jobs = [];

  for (const query of queries) {
    const searchQuery = `(${query}) ("hiring" OR "we're hiring" OR "job opening" OR "now hiring") -is:retweet lang:en`;
    const url = new URL("https://api.x.com/2/tweets/search/recent");
    url.searchParams.set("query", searchQuery);
    url.searchParams.set("start_time", since);
    url.searchParams.set("max_results", "25");
    url.searchParams.set("tweet.fields", "created_at,author_id,entities");
    url.searchParams.set("expansions", "author_id");
    url.searchParams.set("user.fields", "username,name");

    const res = await fetch(url, { headers: { Authorization: `Bearer ${token}` } });
    if (!res.ok) {
      console.warn(`[twitter] "${query}" failed: ${res.status} ${res.statusText}`);
      continue;
    }
    const body = await res.json();
    const users = new Map((body.includes?.users ?? []).map((u) => [u.id, u]));
    for (const t of body.data ?? []) {
      const author = users.get(t.author_id);
      jobs.push({
        id: `twitter:${t.id}`,
        source: "X (Twitter)",
        title: t.text.slice(0, 100),
        company: author?.name ?? "Unknown",
        location: null,
        url: `https://x.com/${author?.username ?? "i"}/status/${t.id}`,
        postedAt: t.created_at,
        remote: /remote/i.test(t.text),
        salary: null,
        description: t.text.slice(0, 280),
        query,
      });
    }
  }
  return jobs;
}
