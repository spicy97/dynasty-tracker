/**
 * config.js — Static configuration for Dynasty Salary Tracker
 *
 * IMPORTANT: This app is READ-ONLY with respect to the Sleeper API.
 * No write operations are made. All data is fetched for display only.
 *
 * League: Big Cock Brock's Fantasy Palooza
 * League ID: 1355351787401383936
 */

const CONFIG = {
  LEAGUE_ID: "1355351787401383936",
  SALARY_CAP: 245,

  /**
   * Default cost for rostered players with no salary-sheet entry and no
   * FAAB bid (typically fresh waiver adds). $0 = unassigned (no cap hit)
   * until the commissioner assigns a salary — either inline on the page
   * (saved in localStorage) or via WAIVER_SALARY_OVERRIDES below.
   */
  WAIVER_FALLBACK_COST: 0,

  /**
   * Manually assigned name/salary for waiver-added players who have no
   * salary-sheet entry yet. Keyed by Sleeper player_id. Outranks both the
   * FAAB bid and the fallback cost. Remove an entry once the sheet carries
   * the player's real salary — the sheet then takes over permanently.
   * (You can also edit any waiver player's salary directly on the page;
   * those edits are saved in your browser's localStorage and win over
   * everything except a real entry in data/salaries.json.)
   */
  WAIVER_SALARY_OVERRIDES: {
    1373: { name: "Geno Smith", salary: 8 }, // Geno Smith (QB) — roster 8
  },

  /**
   * roster_id → { color, emoji, teamName }
   *
   * roster_id is the stable Sleeper key — never key on owner name.
   * Owner display names and avatars are fetched live from the Sleeper API.
   *
   * Resolved via:
   *   GET /v1/league/{id}/rosters  → roster_id → owner_id
   *   GET /v1/league/{id}/users    → owner_id  → metadata.team_name
   */
  TEAM_COLORS: {
    1: { color: "#1565C0", emoji: "🟦", teamName: "The Dicktator" },
    2: { color: "#2E7D32", emoji: "🟩", teamName: "#NewyearNewme" },
    3: { color: "#F9A825", emoji: "🟨", teamName: "Unstoppable Thunderballs" },
    4: { color: "#C8102E", emoji: "🟥", teamName: "Buffalo Buffalo" },
    5: { color: "#6A1B9A", emoji: "🟪", teamName: "Kyle3000" },
    6: { color: "#E65100", emoji: "🟧", teamName: "bringeroftables" },
    7: { color: "#6D4C41", emoji: "🟫", teamName: "Mr. Whatsitt??" },
    8: { color: "#AD1457", emoji: "🌸", teamName: "Your Mom's Favorite Team" },
  },
};
