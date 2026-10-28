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

## Build Execution Principles

> These principles govern how this plan is implemented turn-by-turn to stay within output token limits and keep every file verifiable before moving on.

### One File Per Turn

Each implementation turn produces **exactly one file**, fully written with no stubs or TODOs. Never combine two file implementations in a single response.

### Ascending File Size Order

Work smallest-to-largest so context is fresh when tackling the most complex files.

| Turn | File | Size | Rationale |
|---|---|---|---|
| **1** | `js/config.js` | Tiny | Pure data — team names, colors, emojis |
| **2** | `js/sleeperApi.js` | Small | 3 fetch functions + error handling |
| **3** | `data/salaries.json` | Small | Data-only, no logic |
| **4** | `css/style.css` | Medium | Additive styling — team cards, sections, over-cap highlight |
| **5a** | `js/app.js` (data layer) | Large | fetch, sessionStorage cache, lookup map building |
| **5b** | `js/app.js` (render layer) | Large | `renderTeamCard()`, `renderCapTable()`, timestamp, error states |
| **6** | `scripts/sync-salaries.js` | Medium | Standalone Node script for nightly Google Sheet sync |

### Split `app.js` Into Two Turns

`app.js` is the largest and most complex file. It is always split into two sequential turns:
- **Turn 5a — Data Layer:** fetch, sessionStorage cache, `buildRosterMap()`, `buildSalaryMap()`
- **Turn 5b — Render Layer:** `classifyPlayer()`, `renderTeamCard()`, `renderCapTable()`, `renderTimestamp()`, `showError()`

This split is safe because `app.js` is the last JS file — nothing else imports from it.

### Use Small Named Helper Functions

All logic goes into small, single-purpose named functions — never one large monolithic block. This makes truncation immediately visible and each function independently verifiable.

✅ Good:
```js
function buildSalaryMap(salariesData) { ... }
function classifyPlayer(playerId, roster) { ... }
function renderTeamCard(roster, userMap, salaryMap) { ... }
```

❌ Avoid:
```js
async function init() {
  // 200 lines of inline logic
}
```

### Verify After Every Turn

After each file is written, read it back to confirm:
- No functions contain stubs or TODOs
- No code is visibly truncated mid-block
- The file is syntactically complete

Do not proceed to the next turn until the current file passes verification.

### What to Avoid

- ❌ Never implement two files in one response
- ❌ Never leave a function body as a stub (`// TODO`) in a "completed" file
- ❌ Never use player name strings as lookup keys — always `player_id`
- ❌ Never call `/players/nfl` at runtime

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
├── scripts/
│   └── sync-salaries.js        # Node script for nightly Google Sheet sync (Turn 6)
└── .github/
    └── workflows/
        └── sync-salaries.yml   # (Optional) Nightly GitHub Action
```

---

## Step 3 — Build `data/salaries.json` (Salary Source of Truth)

> **Turn 3** — data-only file, no logic.

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

**✅ Verify:** Confirm `players` object is populated, all entries have `name`, `salary`, and `roster_id`, and the JSON is valid before proceeding.

---

## Step 4 — Build `js/config.js`

> **Turn 1** — smallest file, pure static data. Implement this first.

Stores static config to avoid hardcoding values in logic files:

```js
const CONFIG = {
  LEAGUE_ID: "1355351787401383936",
  SALARY_CAP: 245,
  TEAM_COLORS: {
    1: { color: "#1565C0", emoji: "🟦", teamName: "The Dicktator" },
    2: { color: "#6D4C41", emoji: "🟫", teamName: "Mr. Whatsitt??" },
    // ...all 8 teams
  }
};
```

**✅ Verify:** All 8 `roster_id` entries (1–8) are present in `TEAM_COLORS`, each with a `color`, `emoji`, and `teamName`. No placeholders remain.

---

## Step 5 — Build `js/sleeperApi.js`

> **Turn 2** — small file, 3 fetch functions + shared error handler.

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

### Error Handling Requirements

The shared `sleeperFetch()` wrapper must:
- Throw a typed error distinguishing `429`, `500`, and `503` from other failures
- Allow `app.js` to catch and display a specific user-facing message per error type

**✅ Verify:** All three fetch functions are fully implemented (no `return null` stubs). `sleeperFetch()` handles `429`, `500`, and `503` explicitly.

---

## Step 6 — Build `js/app.js` (Core Logic)

> **Turns 5a and 5b** — largest file, always split into two sequential turns.

### Turn 5a — Data Layer

Implement these named functions:

```
fetchSalaries()             — GET data/salaries.json
loadSleeperData()           — check sessionStorage cache; if miss, call Promise.all([fetchLeague, fetchUsers, fetchRosters]); on success cache; on error throw
buildUserMap(users)         — roster_id → { teamName, ownerName, avatarUrl }
buildSalaryMap(salaries)    — player_id → { name, salary }
```

Cache schema written to `sessionStorage`:
```json
{
  "timestamp": "ISO string",
  "league": { "..." : "..." },
  "users": [ "..." ],
  "rosters": [ "..." ]
}
```

On `429` / `500` / `503`: call `showError()` and return early — do not proceed to render.

**✅ Verify (5a):** All data-layer functions are present and complete. `loadSleeperData()` reads and writes sessionStorage correctly. Error path calls `showError()` and returns.

### Turn 5b — Render Layer

Implement these named functions:

```
classifyPlayer(playerId, roster)           — returns "starter" | "bench" | "taxi" | "ir"
renderTeamCard(roster, userMap, salaryMap) — builds and returns a DOM card element
renderCapTable(rosters, userMap, salaryMap)— populates #cap-table-body rows
renderTimestamp(isoString)                 — sets #sync-timestamp text
showError(message)                         — shows #error-banner, hides #team-grid
init()                                     — orchestrates all of the above on DOMContentLoaded
```

Render rules:
- Guard: if `roster.players` is `null` or empty → render "No players rostered" placeholder, never crash
- Player sections order: Starters → Bench → IR → Taxi Squad
- `player_id` is the key for all lookups — never player name
- Remaining cap shown in **red** if negative (over cap)
- Teams rendered in ascending `roster_id` order

**✅ Verify (5b):** All render-layer functions are present and complete. `classifyPlayer()` covers all four cases. `renderTeamCard()` outputs all four sections. `init()` calls all functions in the correct order.

---

## Step 7 — Build `index.html` and `css/style.css`

> `index.html` is already complete. `css/style.css` is **Turn 4** — implement after `sleeperApi.js`, before `app.js`.

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

### CSS Requirements

The stylesheet must include styles for:
- `.team-card` — card container with colored top border driven by `style` attribute
- `.team-card-header` — banner row with avatar thumbnail, emoji, team name, owner name
- `.section-label` — row label for Starters / Bench / IR / Taxi Squad sections
- `.over-cap` — red text class applied to remaining cap when negative
- All existing base styles (reset, header, error banner, grid, cap table, footer, responsive) preserved

**✅ Verify:** Open `index.html` in a browser with the console open. Confirm no 404s for CSS/JS, no JS errors on load, and the page structure is visible.

---

## Step 8 — Ongoing Salary Maintenance

| Change Type | Source | Action Needed |
|---|---|---|
| Player moves between teams | Sleeper API | ✅ Auto — rosters update live |
| Player cut/added from waivers | Sleeper API | ✅ Auto — reflected in roster arrays |
| New player added via waivers (name + cost) | Sleeper rosters + transactions + nightly `player_names.json` | ✅ Auto — name from `data/player_names.json`; cost = `WAIVER_SALARY_OVERRIDES` (manual, `config.js`) → FAAB bid from `/transactions/{season}` → `WAIVER_FALLBACK_COST` ($1) while bids are unavailable. A sheet salary always wins once entered |
| Salary value changes (trades, extensions) | Google Sheet | 🖊️ Manual — update `salaries.json` |
| New player salary assigned | Google Sheet | 🖊️ Manual — add entry to `salaries.json` |

---

## Step 9 — (Optional) GitHub Action for Auto-Sync

> **Turn 6** — `scripts/sync-salaries.js`. The workflow YAML (`.github/workflows/sync-salaries.yml`) is already complete.

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
- `scripts/sync-salaries.js` must:
  - Accept the Google Sheet CSV export URL (hardcoded or via env var)
  - Parse the CSV into the `salaries.json` schema
  - Write the result to `data/salaries.json` with an updated `last_updated` field
  - Use only Node.js built-ins (`https`, `fs`) — no npm dependencies

> ✅ **GitHub Pages note:** Custom Actions workflows are **exempt** from the standard 10 builds/hour soft limit, so the nightly sync will not count against that quota.

**✅ Verify:** Run `node scripts/sync-salaries.js` locally, confirm `data/salaries.json` is rewritten correctly with a fresh `last_updated` date.

---

## Key Decisions & Tradeoffs

| Decision | Rationale |
|---|---|
| Static site (no server) | GitHub Pages free hosting, no backend needed |
| `salaries.json` in repo | Sleeper has no salary data; this bridges the gap |
| Fetch Sleeper client-side | API is CORS-enabled, small responses, always current |
| Don't call `/players/nfl` on load | It's 5MB; player names come from repo files — `salaries.json` plus `data/player_names.json`, both emitted at build time by the nightly Action. Roster cards display **full first+last names from the Sleeper dataset** (abbreviated sheet names like "A. Rodgers" are replaced at build time) |
| FAAB bid as waiver-add cost | League uses FAAB (`waiver_type: 2`); bids are pulled lazily from `/transactions/{season}` only when a rostered player is missing from the sheet. Empty/failed responses fall back to `CONFIG.WAIVER_FALLBACK_COST` ($1 = `waiver_bid_min`) — no page failure |
| Google Sheet CSV for auto-sync | Keeps salary source-of-truth where managers already edit it |
| One file per turn | Prevents output truncation; every file is verifiable before proceeding |
| `app.js` split into 5a/5b | Largest file — data layer and render layer are independently verifiable |
| Named helper functions only | Makes truncation immediately visible; each function is a clear unit of work |

---

## Next Steps

Follow the **Turn Order** in the Build Execution Principles section above. Start with **Turn 1 — `js/config.js`** (fill in all 8 teams' `TEAM_COLORS`), then proceed in order. Verify each file before moving to the next turn.

