#!/usr/bin/env python3
"""
build_names.py — Nightly name sync (Sleeper-only).

Fetches the Sleeper /players/nfl dataset plus the league's current rosters
and writes data/player_names.json: player_id → {name, position}.

This is the ONLY remaining build step. Salary data in data/salaries.json
is maintained manually in the repo — it is NOT generated from any external
source (the Google Sheet pipeline was retired).

Runs at BUILD TIME only (locally or in GitHub Actions). The browser app
never calls /players/nfl at runtime (see requirements.md, Constraints).

Usage:
    python scripts/build_names.py
"""

import json
import sys
import urllib.request
from pathlib import Path

# Windows consoles default to cp1252 — force UTF-8 so symbols print correctly.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SLEEPER_PLAYERS_URL = "https://api.sleeper.app/v1/players/nfl"
SLEEPER_ROSTERS_URL = "https://api.sleeper.app/v1/league/1355351787401383936/rosters"
REPO_ROOT = Path(__file__).resolve().parent.parent
NAMES_OUTPUT_PATH = REPO_ROOT / "data" / "player_names.json"


def fetch_json(url: str):
    print(f"  GET {url}")
    req = urllib.request.Request(url, headers={"User-Agent": "salary-tracker/1.0"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read())


def main() -> int:
    print("1/2 Fetching Sleeper player dataset (one-time, ~5 MB)…")
    players = fetch_json(SLEEPER_PLAYERS_URL)
    print(f"   Loaded {len(players)} players.")

    print("2/2 Fetching league rosters…")
    rosters = fetch_json(SLEEPER_ROSTERS_URL)
    rostered_ids = {pid for r in rosters for pid in (r.get("players") or [])}
    print(f"   {len(rostered_ids)} players currently rostered.")

    # Every active player plus anyone currently rostered (even if inactive),
    # so waiver adds always resolve to a real name immediately.
    names_out: dict = {}
    for pid, p in players.items():
        if not (p.get("active") or pid in rostered_ids):
            continue
        name = p.get("full_name") or (
            f"{p.get('first_name') or ''} {p.get('last_name') or ''}".strip()
        )
        if not name:
            continue
        names_out[pid] = {
            "name": name,
            "position": (p.get("position") or "").upper(),
        }

    def _sort_key(item):
        pid = item[0]
        return (0, int(pid), "") if pid.isdigit() else (1, 0, pid)

    NAMES_OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(NAMES_OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(dict(sorted(names_out.items(), key=_sort_key)),
                  f, separators=(",", ":"), ensure_ascii=False)
        f.write("\n")

    print(f"✅ Wrote {NAMES_OUTPUT_PATH} ({len(names_out)} players)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
