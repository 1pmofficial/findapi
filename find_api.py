"""
One-off discovery script: sniff JSON API calls made by livesportsontv.com.
Runs on GitHub Actions (headless) and saves results to output/.
"""

import json
from pathlib import Path
from playwright.sync_api import sync_playwright

URL = "https://www.livesportsontv.com"
OUT = Path("output")
OUT.mkdir(parents=True, exist_ok=True)

captured = []


def on_response(response):
    try:
        url = response.url
        ct = response.headers.get("content-type", "")
        if "json" in ct and "livesportsontv" in url:
            body = response.json()
            captured.append({"url": url, "body": body})
            print(f"\n[API FOUND] {url}")
            print(json.dumps(body, indent=2)[:3000])
    except Exception as e:
        print(f"[skip] {response.url} -> {e}")


with sync_playwright() as p:
    # ⚠️ MUST be headless=True on GitHub Actions
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
    page.on("response", on_response)

    print(f"[info] navigating to {URL}")
    try:
        page.goto(URL, wait_until="domcontentloaded", timeout=60000)
    except Exception as e:
        print(f"[warn] goto: {e}")

    # Wait for React to hydrate + fetch
    page.wait_for_timeout(20000)

    # Scroll to trigger lazy loads
    for _ in range(10):
        page.mouse.wheel(0, 2000)
        page.wait_for_timeout(1000)

    # Save rendered HTML
    (OUT / "rendered.html").write_text(page.content(), encoding="utf-8")
    print(f"[info] saved rendered.html")

    browser.close()

# Save captured JSON responses
(OUT / "captured_api.json").write_text(
    json.dumps(captured, indent=2, default=str)[:5_000_000],
    encoding="utf-8",
)
print(f"\n=== Captured {len(captured)} JSON responses ===")
for c in captured:
    print(f"  → {c['url']}")
