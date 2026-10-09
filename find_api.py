"""
Capture the fully rendered HTML of livesportsontv.com AFTER events load.
Events are server-side rendered, not fetched via JSON API.
"""

import re
from pathlib import Path
from playwright.sync_api import sync_playwright

URL = "https://www.livesportsontv.com"
OUT = Path("output")
OUT.mkdir(parents=True, exist_ok=True)


def safe_filename(s: str) -> str:
    """Turn a CSS selector into a safe filename."""
    return re.sub(r"[^A-Za-z0-9_.-]", "_", s)


def main():
    print("[info] launching browser")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/125.0 Safari/537.36"
            ),
            viewport={"width": 1366, "height": 900},
        )
        page = context.new_page()

        # Block ad networks to speed things up
        ad_pattern = re.compile(
            r".*(gumgum|rubiconproject|3lift|media\.net|pub\.network|"
            r"criteo|id5-sync|hadron|audigent|amazon-adsystem|"
            r"btloader|optable|floors\.dev|optimise\.net).*"
        )
        page.route(ad_pattern, lambda route: route.abort())

        print(f"[info] navigating to {URL}")
        try:
            page.goto(URL, wait_until="domcontentloaded", timeout=60000)
        except Exception as e:
            print(f"[warn] goto: {e}")

        # --- Wait for the schedule to actually appear ---
        print("[info] waiting for event rows to render...")
        wait_selectors = [
            "text=/\\d{1,2}:\\d{2}\\s*(AM|PM)/",
            "text=/@/",
            "text=/vs\\./",
        ]
        found = False
        for sel in wait_selectors:
            try:
                page.wait_for_selector(sel, timeout=20000)
                print(f"[info] matched selector: {sel}")
                found = True
                break
            except Exception:
                print(f"[miss] {sel}")

        if not found:
            print("[warn] no event selectors matched — dumping anyway")

        # Scroll to trigger lazy loads
        print("[info] scrolling...")
        for _ in range(15):
            page.mouse.wheel(0, 2500)
            page.wait_for_timeout(800)

        page.mouse.wheel(0, -50000)
        page.wait_for_timeout(3000)

        # --- Dump full HTML ---
        html = page.content()
        (OUT / "rendered.html").write_text(html, encoding="utf-8")
        print(f"[info] rendered.html saved: {len(html):,} bytes")

        # --- Try to locate the actual event list container ---
        print("[info] hunting for event container...")
        candidates = [
            "[class*='eventlist']",
            "[class*='event-list']",
            "[class*='EventList']",
            "[class*='schedule']",
            "main",
        ]
        for candidate in candidates:
            try:
                el = page.query_selector(candidate)
                if el:
                    container_html = el.inner_html()
                    fname = "container_" + safe_filename(candidate) + ".html"
                    (OUT / fname).write_text(container_html, encoding="utf-8")
                    print(f"[hit] container: {candidate} -> {fname}")
                    break
            except Exception as e:
                print(f"[skip] {candidate}: {e}")

        # --- Count time-like strings in the DOM ---
        time_matches = re.findall(r"\b\d{1,2}:\d{2}\s*(?:AM|PM)\b", html)
        print(f"[info] time strings found in HTML: {len(time_matches)}")
        print(f"[info] first 10: {time_matches[:10]}")

        browser.close()

    print("[info] done")


if __name__ == "__main__":
    main()
