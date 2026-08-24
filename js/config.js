/**
 * config.js — Static configuration for Dynasty Salary Tracker
 *
 * IMPORTANT: This app is READ-ONLY with respect to the Sleeper API.
 * No write operations are made. All data is fetched for display only.
 *
 * Step 4 of requirements.md — fill in TEAM_COLORS in that step.
 */

const CONFIG = {
  LEAGUE_ID: "1355351787401383936",
  SALARY_CAP: 245,

  /**
   * roster_id → { color: hex string, emoji: string, teamName: string }
   * Team names and colors populated in Step 4.
   */
  TEAM_COLORS: {
    // Example — to be filled in Step 4:
    // 1: { color: "#1565C0", emoji: "🟦", teamName: "The Dicktator" },
    // 2: { color: "#6D4C41", emoji: "🟫", teamName: "Mr. Whatsitt??" },
  }
};
