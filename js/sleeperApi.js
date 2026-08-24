/**
 * sleeperApi.js — Fetch helpers for the Sleeper API
 *
 * All calls are read-only GET requests. No authentication required.
 * Rate limit: stay under 1,000 calls/minute (we make 3 per page load).
 * Gracefully handles: 429 (rate limit), 500 (server error), 503 (maintenance).
 *
 * Avatar CDN:
 *   Full:      https://sleepercdn.com/avatars/<avatar_id>
 *   Thumbnail: https://sleepercdn.com/avatars/thumbs/<avatar_id>  ← use this in cards
 *
 * Step 5 of requirements.md — logic to be filled in that step.
 */

const SLEEPER_BASE = "https://api.sleeper.app/v1";

/**
 * Shared fetch wrapper — handles non-OK responses and network errors.
 * @param {string} url
 * @returns {Promise<any>}
 */
async function sleeperFetch(url) {
  // TODO (Step 5): implement full error handling for 429 / 500 / 503
  const res = await fetch(url);
  if (!res.ok) {
    throw new Error(`Sleeper API error ${res.status} for ${url}`);
  }
  return res.json();
}

/**
 * GET /v1/league/{league_id}
 * Returns league name, settings, status.
 */
async function fetchLeague(leagueId) {
  // TODO (Step 5)
  return null;
}

/**
 * GET /v1/league/{league_id}/users
 * Returns owner display names, team names, and avatar IDs.
 */
async function fetchUsers(leagueId) {
  // TODO (Step 5)
  return null;
}

/**
 * GET /v1/league/{league_id}/rosters
 * Returns player[], taxi[], reserve[], starters[] arrays per team.
 * NOTE: roster.players may be null during pre-draft / off-season — always guard.
 */
async function fetchRosters(leagueId) {
  // TODO (Step 5)
  return null;
}
