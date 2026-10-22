/**
 * app.js — Main application logic for Dynasty Salary Tracker
 *
 * Flow (see Step 6 of requirements.md):
 *   1. Fetch salaries.json from /data/
 *   2. Check sessionStorage for cached Sleeper data (league, users, rosters)
 *      → If cached: use it (prevents redundant calls on tab refresh)
 *      → If not: fetch all three endpoints in parallel; cache results
 *      → On API error: show error banner, halt render gracefully
 *   3. Build lookup maps: roster_id → owner info, player_id → salary
 *   4. For each roster: classify players (starter/bench/taxi/IR),
 *      sum MAIN salaries (IR + taxi are cap-exempt, matching the sheet),
 *      calc remaining cap
 *   5. Render team cards sorted by roster_id
 *   6. Render cap summary table
 *   7. Show "Last synced with Sleeper: [timestamp]"
 *
 * KEY RULE: player_id is the canonical stable key — never use player name.
 */

const SESSION_KEY = "dynasty_tracker_sleeper_cache";

/* ── Error handling ─────────────────────────────────────────────── */

function showError(message) {
  const banner = document.getElementById("error-banner");
  if (banner) {
    banner.textContent = `⚠️ ${message}`;
    banner.classList.remove("hidden");
  }
  console.error("[dynasty-tracker]", message);
}

/* ── Data loading ───────────────────────────────────────────────── */

/** Fetch data/salaries.json (the salary source of truth). */
async function loadSalaries() {
  const res = await fetch("data/salaries.json");
  if (!res.ok) {
    throw new Error(`Failed to load salaries.json (${res.status})`);
  }
  return res.json();
}

/**
 * Get Sleeper data from sessionStorage, or fetch it fresh.
 * Returns { league, users, rosters, fetchedAt }.
 * Throws SleeperApiError / Error on failure — caller shows the banner.
 */
async function loadSleeperData() {
  const cached = sessionStorage.getItem(SESSION_KEY);
  if (cached) {
    try {
      console.log("[dynasty-tracker] Using cached Sleeper data");
      return JSON.parse(cached);
    } catch {
      sessionStorage.removeItem(SESSION_KEY); // corrupt cache — refetch
    }
  }

  const [league, users, rosters] = await Promise.all([
    fetchLeague(CONFIG.LEAGUE_ID),
    fetchUsers(CONFIG.LEAGUE_ID),
    fetchRosters(CONFIG.LEAGUE_ID),
  ]);

  const data = { league, users, rosters, fetchedAt: Date.now() };
  sessionStorage.setItem(SESSION_KEY, JSON.stringify(data));
  return data;
}

/* ── Lookup maps ────────────────────────────────────────────────── */

/** user_id → user object (display_name, avatar, team_name). */
function buildUserMap(users) {
  const map = new Map();
  for (const u of users) map.set(u.user_id, u);
  return map;
}

/** roster_id → user object (via roster.owner_id). */
function buildOwnerMap(rosters, userMap) {
  const map = new Map();
  for (const r of rosters) {
    map.set(r.roster_id, userMap.get(r.owner_id) || null);
  }
  return map;
}

/** player_id → { name, position, salary, roster_id, section }. */
function buildSalaryMap(salariesData) {
  const map = new Map();
  const players = salariesData.players || {};
  for (const [pid, info] of Object.entries(players)) {
    map.set(pid, info);
  }
  return map;
}

/* ── Roster classification ──────────────────────────────────────── */

/**
 * Classify a roster's players into starters / bench / taxi / ir.
 * Sleeper starters[] can contain "0" for empty slots — those are skipped.
 * Order of checks matters: taxi and reserve override starters.
 */
function classifyPlayers(roster) {
  const result = { starters: [], bench: [], taxi: [], ir: [] };
  const players = roster.players;
  if (!players || players.length === 0) return result; // pre-draft guard

  const taxiSet = new Set(roster.taxi || []);
  const reserveSet = new Set(roster.reserve || []);
  const starterSet = new Set((roster.starters || []).filter((id) => id !== "0"));

  for (const pid of players) {
    if (taxiSet.has(pid)) result.taxi.push(pid);
    else if (reserveSet.has(pid)) result.ir.push(pid);
    else if (starterSet.has(pid)) result.starters.push(pid);
    else result.bench.push(pid);
  }
  return result;
}

/**
 * Sum salaries by section. MAIN total (starters + bench) counts against
 * the cap; IR and taxi are cap-exempt — matching the Google Sheet's own
 * "Salary Total" convention. Players with no salary entry count as $0.
 */
function sumSection(playerIds, salaryMap) {
  let total = 0;
  for (const pid of playerIds) {
    const entry = salaryMap.get(pid);
    if (entry) total += entry.salary;
  }
  return total;
}

function computeCapTotals(classified, salaryMap) {
  const mainTotal = sumSection(classified.starters, salaryMap)
    + sumSection(classified.bench, salaryMap);
  const irTotal = sumSection(classified.ir, salaryMap);
  const taxiTotal = sumSection(classified.taxi, salaryMap);
  return {
    mainTotal,
    irTotal,
    taxiTotal,
    remaining: CONFIG.SALARY_CAP - mainTotal,
  };
}

/* ── Render helpers ─────────────────────────────────────────────── */

/** Team display info: colors from CONFIG, names/avatars from Sleeper. */
function getTeamInfo(rosterId, owner) {
  const colors = CONFIG.TEAM_COLORS[rosterId] || { color: "#555", emoji: "⚪" };
  const teamName = (owner && owner.metadata && owner.metadata.team_name)
    || (owner && owner.display_name)
    || `Team ${rosterId}`;
  const displayName = (owner && owner.display_name) || "Unknown";
  const avatarUrl = owner ? avatarThumbUrl(owner.avatar) : "";
  return { ...colors, teamName, displayName, avatarUrl };
}

/** One player row: name | position | salary. */
function playerRow(pid, salaryMap) {
  const entry = salaryMap.get(pid);
  const name = entry ? entry.name : `Player ${pid}`;
  const pos = entry ? entry.position : "—";
  const salary = entry ? `$${entry.salary}` : "$0";
  return `<tr><td>${name}</td><td>${pos}</td><td class="num">${salary}</td></tr>`;
}

/** A labelled section of the card (Starters / Bench / IR / Taxi). */
function sectionTable(title, playerIds, salaryMap) {
  if (playerIds.length === 0) return "";
  const rows = playerIds.map((pid) => playerRow(pid, salaryMap)).join("");
  return `
    <details class="player-section" open>
      <summary>${title} <span class="count">(${playerIds.length})</span></summary>
      <table class="player-table">
        <thead><tr><th>Player</th><th>Pos</th><th class="num">Salary</th></tr></thead>
        <tbody>${rows}</tbody>
      </table>
    </details>`;
}

/** Full team card element for the grid. */
function renderTeamCard(roster, owner, salaryMap) {
  const rid = roster.roster_id;
  const info = getTeamInfo(rid, owner);
  const classified = classifyPlayers(roster);
  const totals = computeCapTotals(classified, salaryMap);
  const overCap = totals.remaining < 0;

  const card = document.createElement("article");
  card.className = "team-card";
  card.style.setProperty("--team-color", info.color);
  card.innerHTML = `
    <header class="team-card-header">
      <span class="team-emoji">${info.emoji}</span>
      <div>
        <h3 class="team-name">${info.teamName}</h3>
        <p class="team-owner">@${info.displayName}</p>
      </div>
      ${info.avatarUrl ? `<img class="team-avatar" src="${info.avatarUrl}" alt="" loading="lazy">` : ""}
    </header>
    <div class="team-card-body">
      ${roster.players && roster.players.length
        ? sectionTable("Starters", classified.starters, salaryMap)
          + sectionTable("Bench", classified.bench, salaryMap)
          + sectionTable("IR", classified.ir, salaryMap)
          + sectionTable("Taxi Squad", classified.taxi, salaryMap)
        : `<p class="empty-roster">No players rostered (pre-draft / off-season).</p>`}
    </div>
    <footer class="team-card-footer ${overCap ? "over-cap" : ""}">
      <span>Total: <strong>$${totals.mainTotal}</strong></span>
      <span>Remaining: <strong>${overCap ? "-$" + Math.abs(totals.remaining) : "$" + totals.remaining}</strong></span>
    </footer>`;
  return card;
}

/** Cap summary table row for one team. */
function capTableRow(roster, owner, salaryMap) {
  const rid = roster.roster_id;
  const info = getTeamInfo(rid, owner);
  const classified = classifyPlayers(roster);
  const totals = computeCapTotals(classified, salaryMap);
  const overCap = totals.remaining < 0;
  const remainingText = overCap ? `-$${Math.abs(totals.remaining)}` : `$${totals.remaining}`;
  return `
    <tr>
      <td><span class="dot" style="background:${info.color}"></span> ${info.emoji} ${info.teamName}</td>
      <td>@${info.displayName}</td>
      <td class="num">$${totals.mainTotal}</td>
      <td class="num ${overCap ? "negative" : ""}">${remainingText}</td>
    </tr>`;
}

/** "Last synced" timestamp from the cached fetch time. */
function renderTimestamp(fetchedAt) {
  const el = document.getElementById("sync-timestamp");
  if (!el) return;
  const d = new Date(fetchedAt);
  el.textContent = `Last synced with Sleeper: ${d.toLocaleString()}`;
}

/* ── Entry point ────────────────────────────────────────────────── */

async function init() {
  // 1. Salary source of truth (static file)
  let salaries;
  try {
    salaries = await loadSalaries();
  } catch (err) {
    showError("Unable to load salary data — please refresh.");
    return;
  }
  const salaryMap = buildSalaryMap(salaries);

  // 2. Live Sleeper data (cached per session)
  let data;
  try {
    data = await loadSleeperData();
  } catch (err) {
    showError(err.message || "Unable to reach Sleeper — check back shortly.");
    return;
  }

  // 3. Header
  document.getElementById("league-name").textContent = data.league.name || "Dynasty Salary Tracker";
  document.getElementById("salary-cap").textContent = CONFIG.SALARY_CAP;

  // 4. Lookup maps
  const userMap = buildUserMap(data.users);
  const ownerMap = buildOwnerMap(data.rosters, userMap);

  // 5. Team cards (sorted by roster_id)
  const grid = document.getElementById("team-grid");
  grid.innerHTML = "";
  const sorted = [...data.rosters].sort((a, b) => a.roster_id - b.roster_id);
  for (const roster of sorted) {
    grid.appendChild(renderTeamCard(roster, ownerMap.get(roster.roster_id), salaryMap));
  }

  // 6. Cap summary table
  const tbody = document.getElementById("cap-table-body");
  tbody.innerHTML = sorted
    .map((r) => capTableRow(r, ownerMap.get(r.roster_id), salaryMap))
    .join("");

  // 7. Timestamp
  renderTimestamp(data.fetchedAt);
}

document.addEventListener("DOMContentLoaded", init);
