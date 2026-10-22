#!/usr/bin/env python3
"""
validate_salaries.py — Check salaries.json against the live Google Sheet.

Reads the sheet's own "Salary Total" row (per team column) and compares it
to the sum of main+IR salaries in salaries.json. Taxi salaries are excluded
from the cap total, matching the sheet's convention.
"""

import csv
import io
import json
import re
import sys
import urllib.request
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SHEET_CSV_URL = (
    "https://docs.google.com/spreadsheets/d/"
    "1L0hMPOAjNKNmFiuwIJ5YowIKmuMYAhp-IHnjwYWvPjU/export?format=csv&gid=0"
)
REPO = Path(__file__).resolve().parent.parent

# Must match COLUMN_BLOCKS in build_salaries.py
COLUMN_BLOCKS = [
    (0, 1, "The Dicktator"), (4, 7, "TheLongDonSilver"), (8, 2, "WeKenDoIt"),
    (12, 6, "bringeroftables"), (16, 8, "Ajshoemaker9"), (20, 5, "Kyle3000"),
    (24, 3, "Unstoppable Thunderballs"), (28, 4, "spicy97"),
]

data = json.loads((REPO / "data" / "salaries.json").read_text(encoding="utf-8"))
cap = data["salary_cap"]

req = urllib.request.Request(SHEET_CSV_URL, headers={"User-Agent": "x/1.0"})
with urllib.request.urlopen(req, timeout=60) as r:
    rows = list(csv.reader(io.StringIO(r.read().decode("utf-8-sig"))))

# Pull the sheet's own stated totals from the "Salary Total" row
sheet_totals = {}
for row in rows:
    if row and row[0].strip().lower() == "salary total":
        for col, rid, label in COLUMN_BLOCKS:
            if col + 2 < len(row):
                m = re.search(r"-?\d+", row[col + 2])
                if m:
                    sheet_totals[rid] = (label, int(m.group()))
        break

if not sheet_totals:
    print("ERROR: could not find 'Salary Total' row in sheet")
    sys.exit(1)

print(f"Cap: ${cap} | Players in salaries.json: {len(data['players'])}\n")
fail = False
for rid in sorted(sheet_totals):
    label, expected = sheet_totals[rid]
    # The sheet's "Salary Total" counts the MAIN roster only — IR and taxi
    # are cap-exempt (verified: sheet Remaining = 245 - main total).
    actual = sum(p["salary"] for p in data["players"].values()
                 if p["roster_id"] == rid and p["section"] == "main")
    ok = actual == expected
    if not ok:
        fail = True
    mark = "OK " if ok else "MISMATCH"
    print(f"[{mark}] roster {rid} {label:28} json ${actual:>4}  sheet ${expected:>4}")

print()
if fail:
    print("Note: mismatches are expected for stale sheet entries the build")
    print("flagged (cut/traded players still listed in the sheet).")
    sys.exit(1)
print("All rosters match the sheet totals.")
sys.exit(0)
