/**
 * sleeperApi.js — Fetch helpers for the Sleeper API
 *
 * All calls are read-only GET requests. No authentication required.
 * Rate limit: stay under 1,000 calls/minute (we make 3 per page load).
 *
 * Avatar CDN:
 *   Full:      https://sleepercdn.com/avatars/<avatar_id>
 *   Thumbnail: https://sleepercdn.com/avatars/thumbs/<avatar_id>  ← used in team cards
 *
 * This app is NOT affiliated with or endorsed by Sleeper.
 */

const SLEEPER_BASE = "https://api.sleeper.app/v1";

/**
 * Error class that carries the HTTP status code so callers can
 * distinguish 429 / 500 / 503 from generic network failures.
 */
class SleeperApiError extends Error {
  constructor(status, url) {
    const messages = {
      429: "Sleeper API rate limit reached (429) — please wait a moment and try again.",
      500: "Sleeper API server error (500) — check back shortly.",
      503: "Sleeper API is under maintenance (503) — check back shortly.",
    };
    super(messages[status] || `Sleeper API error ${status} for ${url}`);
    this.status = status;
    this.url = url;
    this.name = "SleeperApiError";
  }
}

/**
 * Shared fetch wrapper.
 * Throws SleeperApiError for 429 / 500 / 503 and any other non-OK status.
 * Throws a plain Error for network-level failures (offline, DNS, etc.).
 *
 * @param {string} url
 * @returns {Promise<any>} Parsed JSON response
 */
async function sleeperFetch(url) {
  let res;
  try {
    res = await fetch(url);
  } catch (networkErr) {
    throw new Error(
      "Unable to reach Sleeper — check your connection and try again."
    );
  }

  if (!res.ok) {
    throw new SleeperApiError(res.status, url);
  }

  return res.json();
}

/**
 * GET /v1/league/{league_id}
 * Returns league name, season, status, and settings.
 *
 * @param {string} leagueId
 * @returns {Promise<Object>}
 */
async function fetchLeague(leagueId) {
  return sleeperFetch(`${SLEEPER_BASE}/league/${leagueId}`);
}

/**
 * GET /v1/league/{league_id}/users
 * Returns an array of user objects with display_name, avatar, and
 * metadata.team_name for each manager in the league.
 *
 * @param {string} leagueId
 * @returns {Promise<Array>}
 */
async function fetchUsers(leagueId) {
  return sleeperFetch(`${SLEEPER_BASE}/league/${leagueId}/users`);
}

/**
 * GET /v1/league/{league_id}/rosters
 * Returns an array of roster objects. Key fields per roster:
 *   roster_id  {number}        — stable integer key
 *   owner_id   {string}        — maps to user.user_id
 *   players    {string[]|null} — all player IDs (null in pre-draft / off-season)
 *   starters   {string[]}      — player IDs in starting slots
 *   taxi       {string[]|null} — player IDs on taxi squad
 *   reserve    {string[]|null} — player IDs on IR
 *
 * NOTE: players may be null — always guard before iterating.
 *
 * @param {string} leagueId
 * @returns {Promise<Array>}
 */
async function fetchRosters(leagueId) {
  return sleeperFetch(`${SLEEPER_BASE}/league/${leagueId}/rosters`);
}

/**
 * GET /v1/league/{league_id}/transactions/{season}
 * Returns every transaction for the season (waivers, trades, adds/drops).
 * We only care about completed waiver claims: settings.waiver_bid is the
 * FAAB amount spent. The latest claim for each rostered player overrides
 * their baseline salary from salaries.json.
 *
 * NOTE: Sleeper has intermittently returned [] for this endpoint. Callers
 * must treat an empty array as "no bid data" and fall back gracefully.
 *
 * @param {string} leagueId
 * @param {string} season — e.g. "2026"
 * @returns {Promise<Array>}
 */
async function fetchTransactions(leagueId, season) {
  return sleeperFetch(`${SLEEPER_BASE}/league/${leagueId}/transactions/${season}`);
}

/**
 * Returns the thumbnail avatar URL for a given Sleeper avatar ID.
 * Falls back to an empty string if no avatar ID is provided.
 *
 * @param {string|null} avatarId
 * @returns {string}
 */
function avatarThumbUrl(avatarId) {
  if (!avatarId) return "";
  return `https://sleepercdn.com/avatars/thumbs/${avatarId}`;
}
