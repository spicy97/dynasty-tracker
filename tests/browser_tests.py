#!/usr/bin/env python3
"""Run FAAB regression tests and a live Sleeper smoke test in headless Chrome."""

from functools import partial
from html import unescape
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import os
import re
import shutil
import subprocess
import tempfile
import threading

ROOT = Path(__file__).resolve().parent.parent
REGRESSION_URL = (ROOT / "tests" / "faab.test.html").as_uri()
CHROME_CANDIDATES = (
    shutil.which("chrome"),
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
)


def chrome_path() -> str:
    for candidate in CHROME_CANDIDATES:
        if candidate and os.path.isfile(candidate):
            return candidate
    raise RuntimeError("Install Google Chrome or Microsoft Edge to run browser tests")


def render(url: str, budget_ms: int) -> str:
    with tempfile.TemporaryDirectory(prefix="salary-tracker-browser-") as profile:
        command = [
            chrome_path(),
            "--headless=new",
            "--disable-gpu",
            "--no-first-run",
            "--no-default-browser-check",
            "--allow-file-access-from-files",
            f"--user-data-dir={profile}",
            f"--virtual-time-budget={budget_ms}",
            "--dump-dom",
            url,
        ]
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=75,
            check=False,
        )
    if result.returncode != 0:
        raise AssertionError(f"Browser exited {result.returncode}: {result.stderr[-2000:]}")
    return result.stdout


def run_regression_tests() -> None:
    dom = render(REGRESSION_URL, budget_ms=3000)
    match = re.search(r'<pre id="test-results">(.*?)</pre>', dom, re.DOTALL)
    assert match, "Regression page did not produce a test result"
    output = unescape(match.group(1))
    print(output)
    assert "FAIL" not in output, "At least one FAAB regression test failed"
    summary = re.search(r"(\d+)/(\d+) tests passed", output)
    assert summary and summary.group(1) == summary.group(2), "Incomplete regression run"


def run_live_smoke_test() -> None:
    handler = partial(SimpleHTTPRequestHandler, directory=str(ROOT))
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        url = f"http://127.0.0.1:{server.server_address[1]}/"
        dom = render(url, budget_ms=20000)
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)

    teams = dom.count('class="team-card"')
    faab_salaries = dom.count("Current FAAB acquisition")
    unknown_salaries = dom.count("Salary unknown")
    error = re.search(r'<div id="error-banner" class="([^"]*)"', dom)
    print(
        f"Live smoke test: {teams} teams, {faab_salaries} FAAB salaries, "
        f"{unknown_salaries} unknown salaries"
    )
    assert teams == 8, f"Expected 8 rendered teams, found {teams}"
    assert faab_salaries > 0, "No live FAAB salaries were rendered"
    assert error and "hidden" in error.group(1), "Application error banner is visible"


if __name__ == "__main__":
    run_regression_tests()
    run_live_smoke_test()
    print("All browser checks passed.")
