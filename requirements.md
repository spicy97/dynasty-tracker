# 🏈 GitHub Pages Fantasy Salary Tracker — Build Plan

## Overview

A fully static site (no server required) hosted on **GitHub Pages** that:

- Fetches live roster data from the **Sleeper API** on every page load
- Reads salary data from a maintained `salaries.json` file in the repo (seeded from the Google Sheet)
- Merges both sources to display team rosters, salary totals, cap space, and IR/Taxi designations

---

## Constraints, Rules & Guidelines

> Sourced from the [Sleeper API docs](https://docs.sleeper.com/) and [GitHub Pages official limits](https://docs.github.com/en/pages/getting-started-with-github-pages/github-pages-limits).

### Sleeper API

| Rule | Detail |
|---|---|
| **License** | Free for **non-commercial use only** — this private league tool qualifies ✅ |
| **Rate limit** | Stay under **1,000 API calls/minute** or risk IP block (`429` response) |
| **`/players/nfl`** | Must **never be called at runtime** — it's ~5MB and intended for once-per-day server-side use only |
| **Trending data** | Requires **attribution to Sleeper** if embedded or displayed |
| **Authentication** | None required — the API is entirely read-only |
| **Error handling** | Must gracefully handle `429` (rate limited), `500` (server error), and `503` (maintenance) with a visible user-facing error state |
| **Pre-draft / off-season** | `roster.players` may be `null` or empty — render a safe placeholder, never crash |

### GitHub Pages

| Limit | Value |
|---|---|
| **Repo size** | Recommended max **1 GB** — keep `salaries.json` lean, no binary blobs |
| **Published site size** | Hard max **1 GB** |
| **Bandwidth** | Soft limit **100 GB/month** |
| **Build timeout** | **10 minutes** max per deployment |
| **Build frequency** | Soft limit 10 builds/hour — **custom Actions workflows (Step 9) are exempt** ✅ |
| **Prohibited use** | No commercial transactions, SaaS, or sensitive user data (passwords, payment info) |

### Best Practices (from similar open-source projects)

- **`player_id` is the canonical stable key** everywhere — never key data on player name strings (names can change, contain duplicates, or drift across sources)
- **Cache Sleeper API responses in `sessionStorage`** on each page load — prevents redundant calls on tab refresh without going stale between sessions
- **Non-affiliation disclaimer** must appear in the site footer: *"This tool is not affiliated with or endorsed by Sleeper"*
- **Document read-only intent** in `config.js` — no write operations to Sleeper are possible or attempted via this API

---

## Step 1 — Create & Configure the GitHub Repository

1. Create a new repo (e.g., `dynasty-tracker`) under your GitHub account
2. Go to **Settings → Pages → Source:** `main` branch, `/` (root) folder
3. The site will be live at:
   ```
   https://<your-username>.github.io/dynasty-tracker/
   ```

---

## Step 2 — File Structure

```
dynasty-tracker/
├── index.html                  # Single-page app shell
├── css/
│   └── style.css               # Styling, team colors, responsive layout
├── js/
│   ├── config.js               # League ID, salary cap, team color map
│   ├── sleeperApi.js           # Fetch helpers for Sleeper endpoints
│   └── app.js                  # Main logic: fetch → merge → render
├── data/
│   └── salaries.json           # Player ID → salary mapping (source of truth)
└── .github/
    └── workflows/
        └── sync-salaries.yml   # (Optional) Nightly GitHub Action
```

---

## Step 3 — Build `data/salaries.json` (Salary Source of Truth)

Since salaries aren't stored in Sleeper, this JSON file maps Sleeper player IDs → salary and metadata. It is seeded manually from the Google Sheet.

### Structure

```json
{
  "last_updated": "2026-08-23",
  "salary_cap": 245,
  "players": {
    "4034": { "name": "Bijan Robinson",   "salary": 59, "roster_id": 1 },
    "6804": { "name": "Jahmyr Gibbs",     "salary": 42, "roster_id": 1 },
    "7563": { "name": "Justin Jefferson", "salary": 73, "roster_id": 7 }
  }
}
```

### Initial Build Process

Cross-reference player names from the Google Sheet against Sleeper player IDs from the rosters API. A one-time setup script (Node.js or Python) can automate name→ID matching using the `/players/nfl` endpoint.

> ⚠️ **Key rule:** Once a player's Sleeper `player_id` is confirmed and written into `salaries.json`, the **ID is the source of truth** — not the name. Player names in the JSON are for human readability only and should not be used as lookup keys in code.

---

## Step 4 — Build `js/config.js`

Stores static config to avoid hardcoding values in logic files:

```js
const CONFIG = {
  LEAGUE_ID: "1355351787401383936",
  SALARY_CAP: 245,
  TEAM_COLORS: {
    1: { color: "#1565C0", emoji: "🟦" },   // The Dicktator
    2: { color: "#6D4C41", emoji: "🟫" },   // Mr. Whatsitt??
    // ...etc
  }
};
```

---

## Step 5 — Build `js/sleeperApi.js`

Three fetch calls made **in parallel** on page load:

| Endpoint | Returns |
|---|---|
| `GET /v1/league/{id}` | League name, settings |
| `GET /v1/league/{id}/users` | Owner names, team names, avatars |
| `GET /v1/league/{id}/rosters` | Player arrays + taxi/reserve/starters |

### Roster Response Fields Used

| Field | Meaning |
|---|---|
| `players[]` | All player IDs on the roster |
| `taxi[]` | Players on taxi squad |
| `reserve[]` | Players on IR |
| `starters[]` | Players in starting lineup (vs. bench) |

### Avatar CDN URLs (from Sleeper docs)

| Size | URL Pattern |
|---|---|
| Full size | `https://sleepercdn.com/avatars/<avatar_id>` |
| Thumbnail | `https://sleepercdn.com/avatars/thumbs/<avatar_id>` |

Use the **thumbnail** URL for team card headers to minimise load time.

---

## Step 6 — Build `js/app.js` (Core Logic)

```
on page load:
  1. Fetch salaries.json (from /data/)
  2. Check sessionStorage for cached Sleeper data (league, users, rosters)
       → If cache exists and is from this session: use it, skip API calls
       → If no cache: fetch Promise.all([league, users, rosters]) from Sleeper API
            → On success: write results to sessionStorage with timestamp
            → On 429/500/503: show error banner ("Unable to reach Sleeper —
              check back shortly") and halt render gracefully
  3. Build lookup maps:
       roster_id  → user/team info
       player_id  → salary (from salaries.json)
  4. For each roster:
       a. Guard: if roster.players is null/empty, render "No players rostered" placeholder
       b. Classify each player: starter | bench | taxi | IR
            (player_id is the key — never player name)
       c. Look up salary from salaries.json by player_id
       d. Sum salaries → total used
       e. Calculate remaining cap = SALARY_CAP - total
  5. Render team cards in sorted order (by roster_id)
  6. Render cap summary table at bottom
  7. Show "Last synced with Sleeper: [timestamp]"
```

---

## Step 7 — Build `index.html` and `css/style.css`

### Layout

- **Header:** League name and salary cap
- **Grid of 8 team cards**, each showing:
  - Team color banner + emoji + team name + owner
  - Table: `Player | Position | Salary`
  - Sections: Starters → Bench → IR → Taxi Squad
  - Footer row: Total Salary | Remaining Cap *(red if over cap)*
- **Bottom:** Cap Summary table with all 8 teams side-by-side
- **Fully responsive** (works on mobile)
- **Footer disclaimer:** *"This tool is not affiliated with or endorsed by Sleeper. Roster data is fetched live from the Sleeper API."*

---

## Step 8 — Ongoing Salary Maintenance

| Change Type | Source | Action Needed |
|---|---|---|
| Player moves between teams | Sleeper API | ✅ Auto — rosters update live |
| Player cut/added from waivers | Sleeper API | ✅ Auto — reflected in roster arrays |
| Salary value changes (trades, extensions) | Google Sheet | 🖊️ Manual — update `salaries.json` |
| New player salary assigned | Google Sheet | 🖊️ Manual — add entry to `salaries.json` |

---

## Step 9 — (Optional) GitHub Action for Auto-Sync

**`.github/workflows/sync-salaries.yml`**

```yaml
on:
  schedule:
    - cron: '0 6 * * *'   # 6am UTC daily
  workflow_dispatch:       # also allow manual trigger

jobs:
  sync:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
      - run: node scripts/sync-salaries.js  # Downloads Sheet CSV, rebuilds salaries.json
      - run: |
          git config user.name "github-actions"
          git add data/salaries.json
          git commit -m "chore: sync salaries from Google Sheet" || echo "No changes"
          git push
```

### Requirements

- Google Sheet must be **publicly viewable** (Share → Anyone with link → Viewer)
- A `scripts/sync-salaries.js` Node script that parses the CSV and writes `salaries.json`

> ✅ **GitHub Pages note:** Custom Actions workflows are **exempt** from the standard 10 builds/hour soft limit, so the nightly sync will not count against that quota.

---

## Key Decisions & Tradeoffs

| Decision | Rationale |
|---|---|
| Static site (no server) | GitHub Pages free hosting, no backend needed |
| `salaries.json` in repo | Sleeper has no salary data; this bridges the gap |
| Fetch Sleeper client-side | API is CORS-enabled, small responses, always current |
| Don't call `/players/nfl` on load | It's 5MB; player names come from `salaries.json` instead |
| Google Sheet CSV for auto-sync | Keeps salary source-of-truth where managers already edit it |

---

## Next Steps

Build the full site — all files, the initial `salaries.json` seeded from roster data, the GitHub Action, and complete HTML/CSS/JS.

