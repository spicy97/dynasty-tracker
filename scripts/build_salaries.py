#!/usr/bin/env python3
"""
build_salaries.py — Seed / nightly sync script.

Reads the Google Sheet salary CSV, matches each player name to a Sleeper
player_id using the Sleeper /players/nfl dataset, and writes data/salaries.json.

IMPORTANT: This script runs at BUILD TIME only (locally or in GitHub Actions).
The browser app NEVER calls /players/nfl at runtime — player names are read
from salaries.json instead (see requirements.md, Constraints section).

Usage:
    python scripts/build_salaries.py
"""

import csv
import io
import json
import re
import sys
import urllib.request
from datetime import date
from pathlib import Path

# Windows consoles default to cp1252 — force UTF-8 so symbols print correctly.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# ── Configuration ────────────────────────────────────────────────────────────

SHEET_CSV_URL = (
    "https://docs.google.com/spreadsheets/d/"
    "1L0hMPOAjNKNmFiuwIJ5YowIKmuMYAhp-IHnjwYWvPjU/export?format=csv&gid=0"
)
SLEEPER_PLAYERS_URL = "https://api.sleeper.app/v1/players/nfl"
SLEEPER_ROSTERS_URL = "https://api.sleeper.app/v1/league/1355351787401383936/rosters"
SALARY_CAP = 245

# Column block index (0-based) → (sleeper roster_id, owner/team label).
# Derived from the Google Sheet column order, cross-checked against
# Sleeper /users owner_ids and /rosters roster_ids.
COLUMN_BLOCKS = [
    (0, 1,  "The Dicktator (noah28miller)"),
    (4, 7,  "TheLongDonSilver"),
    (8, 2,  "WeKenDoIt"),
    (12, 6, "bringeroftables"),
    (16, 8, "Ajshoemaker9"),
    (20, 5, "Kyle3000"),
    (24, 3, "Unstoppable Thunderballs (clyon98)"),
    (28, 4, "spicy97"),
]

REPO_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_PATH = REPO_ROOT / "data" / "salaries.json"

# ── Manual overrides ─────────────────────────────────────────────────────────
# Name collisions or format differences the fuzzy matcher could not resolve.
# Key: (normalized_last_name, roster_id, salary) → Sleeper player_id.
# Salary is included so two same-name players on one roster (e.g. Bijan vs
# Brian Robinson) resolve correctly. Verified against live Sleeper rosters.
MANUAL_OVERRIDES = {
    ("robinson", 1, 59): "9509",   # Bijan Robinson        (RB) — "B Robinson $59"
    ("robinson", 1, 1):  "8154",   # Brian Robinson Jr.    (RB) — "B. Robinson Jr $1"
    ("anderson", 1, 1):  "10892",  # Will Anderson Jr.     (DL, HOU) — listed as "W. Anderson IDP"
    ("downs", 1, 1):     "9500",   # Josh Downs            (WR, IND)
    ("higgens", 1, 4):   "12484",  # Jayden Higgins        (WR, HOU) — sheet misspells "Higgens"
    ("burden", 2, 7):    "12519",  # Luther Burden III     (WR, CHI)
    ("concepcion", 3, 15): "13298",# KC Concepcion Jr.     (WR, CLE)
    ("fannin", 4, 3):    "12506",  # Harold Fannin Jr.     (TE, CLE)
    ("monangui", 4, 3):  "12534",  # Kyle Monangai         (RB, CHI) — sheet spells "Monangui"
    ("walker", 5, 18):   "8151",   # Kenneth Walker III    (RB, KC)
    ("cooper", 5, 8):    "13276",  # Omar Cooper Jr.       (WR, NYJ)
    ("penix", 6, 3):     "11559",  # Michael Penix Jr.     (QB, ATL)
    ("bain", 6, 2):      "13340",  # Rueben Bain Jr.       (DL, TB) — listed as "R. Bain IDP"
    ("jones", 8, 3):     "4199",   # Aaron Jones Sr.       (RB, MIN)
}


# ── Helpers ──────────────────────────────────────────────────────────────────

def normalize_last(name: str) -> str:
    """
    Normalize a last name for matching.
    'Smith-Njigba' → 'smithnjigba'
    'Etienne Jr.' → 'ettienne'  (suffixes stripped)
    'Samuel Sr.'  → 'samuel'
    'Cook III'    → 'cook'
    """
    s = name.lower()
    # Drop common suffixes before stripping punctuation
    s = re.sub(r"\b(jr|sr|ii|iii|iv|v)\b\.?", "", s)
    return re.sub(r"[^a-z]", "", s)


def first_initial(name: str) -> str:
    """'Justin Jefferson' → 'j' ; 'B Robinson' → 'b'"""
    return name.strip()[0].lower() if name.strip() else ""


def split_name(raw: str) -> tuple:
    """
    Split a CSV cell like 'J. Jefferson', 'B Robinson' or 'J.Downs'
    into (first_name, last_name) → ('J', 'Jefferson').
    """
    cleaned = raw.strip()
    # Handle 'J.Downs' — initial glued to the last name with a period
    if " " not in cleaned and "." in cleaned:
        first_part, _, rest = cleaned.partition(".")
        if len(first_part) <= 2 and rest:
            return first_part, rest
    parts = cleaned.split()
    if len(parts) < 2:
        return "", cleaned
    first = parts[0].rstrip(".")
    last = " ".join(parts[1:])
    return first, last


def fetch_url(url: str) -> bytes:
    print(f"  GET {url}")
    req = urllib.request.Request(url, headers={"User-Agent": "salary-tracker/1.0"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return resp.read()


def parse_salary_csv(csv_text: str) -> list:
    """
    Parse the multi-column Google Sheet CSV.

    Returns a list of entries:
      { name, position, salary, roster_id, section }
    where section is 'main' | 'ir' | 'taxi'.
    """
    rows = list(csv.reader(io.StringIO(csv_text)))
    entries = []
    section = "main"

    for row in rows:
        if not row or all(cell.strip() == "" for cell in row):
            continue

        first_cell = row[0].strip().lower() if row else ""
        if first_cell == "ir":
            section = "ir"
            continue
        if first_cell.startswith("taxi"):
            section = "taxi"
            continue
        if first_cell in ("salary total", "remaining cap space", "salary cap"):
            section = "done"
            continue
        if section == "done":
            continue
        if first_cell == "player":
            continue

        has_salary = any("$" in cell for cell in row)
        if not has_salary:
            continue

        for col_base, roster_id, _label in COLUMN_BLOCKS:
            if col_base + 2 >= len(row):
                continue
            name_cell = row[col_base].strip()
            pos_cell = row[col_base + 1].strip()
            sal_cell = row[col_base + 2].strip()

            if not name_cell or not pos_cell or not sal_cell:
                continue
            if name_cell.lower() in ("player", "salary total", "remaining cap space"):
                continue
            if not sal_cell.startswith("$"):
                continue

            try:
                salary = int(sal_cell.replace("$", "").strip())
            except ValueError:
                print(f"  ⚠ Could not parse salary '{sal_cell}' for '{name_cell}'")
                continue

            entries.append({
                "name": name_cell,
                "position": pos_cell.upper(),
                "salary": salary,
                "roster_id": roster_id,
                "section": section,
            })

    return entries


def build_player_index(sleepers: dict) -> dict:
    """
    Build {norm_last: [ {id, full_name, first, position, team}, ... ]}
    from the Sleeper /players/nfl response.
    """
    index: dict = {}
    for pid, p in sleepers.items():
        last = p.get("last_name") or ""
        if not last:
            continue
        key = normalize_last(last)
        index.setdefault(key, []).append({
            "id": pid,
            "full_name": p.get("full_name", ""),
            "first": first_initial(p.get("first_name", "")),
            "position": (p.get("position") or "").upper(),
            "team": p.get("team") or "",
        })
    return index


def match_player(entry: dict, index: dict, roster_players: set):
    """
    Match a CSV entry (name like 'J. Jefferson', position 'WR', salary $73)
    to a Sleeper player_id.

    Strategy (in priority order):
      1. Roster membership — we know exactly which player_ids are on each
         Sleeper roster, so a candidate who is actually on this roster is
         the correct match. This resolves name collisions definitively.
      2. Filter by last name (normalized).
      3. Filter by first initial if available.
      4. Filter by position.
      5. If still >1 candidate, flag as ambiguous for manual review.
    """
    first, last = split_name(entry["name"])
    if not last:
        return None

    # Step 0: manual override for known name collisions / sheet typos
    key = normalize_last(last)
    override = MANUAL_OVERRIDES.get((key, entry["roster_id"], entry["salary"]))
    if override:
        return override

    candidates = index.get(key, [])
    if not candidates:
        return None

    # Step 1: roster membership is a HARD requirement — we know exactly which
    # player_ids are on each Sleeper roster, so a candidate not on this roster
    # is the wrong player (or was cut/traded; either way, flag for review).
    on_roster = [c for c in candidates if c["id"] in roster_players]
    if not on_roster:
        names = ", ".join(f"{c['full_name']} ({c['id']})" for c in candidates)
        print(f"  ⚠ NOT ON ROSTER {entry['roster_id']}: {entry['name']} "
              f"[{entry['position']}] → name matches only: {names}")
        return None
    candidates = on_roster  # same last name on same roster — narrow further

    if first:
        filtered = [c for c in candidates if c["first"] == first.lower()]
        if filtered:
            candidates = filtered

    if entry["position"]:
        filtered = [c for c in candidates if c["position"] == entry["position"]]
        if filtered:
            candidates = filtered

    if len(candidates) == 1:
        return candidates[0]["id"]

    if len(candidates) > 1:
        names = ", ".join(f"{c['full_name']} ({c['id']})" for c in candidates)
        print(f"  ⚠ AMBIGUOUS: {entry['name']} [{entry['position']}] "
              f"roster {entry['roster_id']} → {names}")
        return None

    return None


# ── Main ─────────────────────────────────────────────────────────────────────

def main() -> int:
    print("1/3 Fetching Sleeper player dataset (one-time, ~5 MB)…")
    raw = fetch_url(SLEEPER_PLAYERS_URL)
    sleeper_players = json.loads(raw)
    print(f"   Loaded {len(sleeper_players)} players.")

    print("2/3 Fetching salary CSV and Sleeper rosters…")
    csv_bytes = fetch_url(SHEET_CSV_URL)
    csv_text = csv_bytes.decode("utf-8-sig")
    entries = parse_salary_csv(csv_text)
    print(f"   Parsed {len(entries)} salary entries.")

    rosters_raw = fetch_url(SLEEPER_ROSTERS_URL)
    rosters = json.loads(rosters_raw)
    # roster_id → set of player_ids actually on that Sleeper roster
    roster_map: dict = {}
    for r in rosters:
        roster_map[r["roster_id"]] = set(r.get("players") or [])
    print(f"   Loaded {len(roster_map)} rosters.")

    if not entries:
        print("ERROR: No salary entries parsed — check sheet format.")
        return 1

    print("3/3 Matching player names to Sleeper IDs…")
    player_index = build_player_index(sleeper_players)

    players_out: dict = {}
    unmatched: list = []

    for entry in entries:
        roster_ids = roster_map.get(entry["roster_id"], set())
        pid = match_player(entry, player_index, roster_ids)
        if pid is None:
            unmatched.append(entry)
            continue

        players_out[pid] = {
            "name": entry["name"],
            "position": entry["position"],
            "salary": entry["salary"],
            "roster_id": entry["roster_id"],
            "section": entry["section"],
        }

    output = {
        "last_updated": date.today().isoformat(),
        "salary_cap": SALARY_CAP,
        "players": dict(sorted(players_out.items(), key=lambda x: int(x[0]))),
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
        f.write("\n")

    print(f"\n✅ Wrote {OUTPUT_PATH}")
    print(f"   {len(players_out)} players matched, {len(unmatched)} unmatched.")

    if unmatched:
        print("\n⚠ UNMATCHED (stale sheet entries or new players — "
              "add to MANUAL_OVERRIDES or update the sheet):")
        for e in unmatched:
            print(f"   roster {e['roster_id']:>2} | {e['section']:>5} | "
                  f"{e['name']:25} | {e['position']:4} | ${e['salary']}")

    # Unmatched entries do NOT fail the build — they are usually stale sheet
    # rows for players since cut/traded. salaries.json still writes correctly.
    return 0


if __name__ == "__main__":
    sys.exit(main())
