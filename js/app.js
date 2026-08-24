/**
 * app.js — Main application logic for Dynasty Salary Tracker
 *
 * Flow (see Step 6 of requirements.md):
 *   1. Fetch salaries.json from /data/
 *   2. Check sessionStorage for cached Sleeper data
 *      → If cached: use it
 *      → If not: fetch league, users, rosters in parallel; cache results
 *      → On API error: show error banner, halt render
 *   3. Build lookup maps (roster_id → user, player_id → salary)
 *   4. For each roster: classify players, sum salaries, calc cap space
 *   5. Render team cards
 *   6. Render cap summary table
 *   7. Show last-synced timestamp
 *
 * KEY RULE: player_id is the canonical stable key — never use player name as a key.
 *
 * Step 6 of requirements.md — logic to be filled in that step.
 */

const SESSION_KEY = "dynasty_tracker_sleeper_cache";

/**
 * Shows the error banner and hides the main grid.
 */
function showError(message) {
  const banner = document.getElementById("error-banner");
  if (banner) {
    banner.textContent = `⚠️ ${message}`;
    banner.classList.remove("hidden");
  }
  console.error("[dynasty-tracker]", message);
}

/**
 * Entry point — called on DOMContentLoaded.
 */
async function init() {
  // TODO (Step 6): implement full fetch → merge → render pipeline
  console.log("[dynasty-tracker] init() — scaffold stub, Step 6 will implement this.");
  console.log("CONFIG:", CONFIG);
}

document.addEventListener("DOMContentLoaded", init);
