"""Optional offline browser checks. Run with uv run --no-project --with playwright.

Uses an existing Chrome installation. Screenshots may contain private report text.
"""
import argparse
from datetime import date, timedelta
from pathlib import Path

from playwright.sync_api import sync_playwright


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path)
    parser.add_argument("--chrome", default="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
    parser.add_argument("--screenshots", type=Path)
    args = parser.parse_args()
    if args.screenshots:
        args.screenshots.mkdir(parents=True, mode=0o700, exist_ok=True)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True, executable_path=args.chrome)
        try:
            context = browser.new_context(offline=True, viewport={"width": 1280, "height": 960},
                                          reduced_motion="reduce")
            page = context.new_page()
            errors, external = [], []
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.on("console", lambda message: errors.append(message.text) if message.type == "error" else None)
            page.on("request", lambda request: external.append(request.url) if request.url.startswith(("https:", "http:")) else None)
            page.goto(args.report.resolve().as_uri(), wait_until="load")
            assert page.locator("h1").inner_text().strip()
            count = page.locator("#repo-table tbody tr").count()
            assert count > 0
            original_date = page.locator("#report-date").input_value()
            another_day = (date.fromisoformat(original_date) - timedelta(days=1)).isoformat()
            page.locator("#report-date").fill(another_day)
            assert another_day in page.locator("#date-command").inner_text()
            page.locator("#report-date").fill(original_date)
            for agent, command in (("pi", "/skill:daily-report"), ("codex", "$daily-report"),
                                   ("claude", "/context:daily-report")):
                page.locator("#report-agent").select_option(agent)
                assert page.locator("#date-command").inner_text() == f"{command} {original_date}"
            page.locator("#report-agent").select_option("pi")
            citations = page.locator("a.citation")
            if citations.count():
                reference = citations.first.get_attribute("href")
                citations.first.click()
                assert page.locator("#audit").evaluate("element => element.open")
                assert page.locator(reference).evaluate("element => element.open")
            page.locator("#audit").evaluate("element => element.open = true")
            page.locator("#inventory").evaluate("element => element.open = true")
            page.locator("#repo-search").fill("no-such-checkout-987654321")
            assert page.locator("#repo-table tbody tr:visible").count() == 0
            assert page.locator("#search-count").inner_text() == "0 checkouts"
            page.locator("#repo-search").fill("")
            assert page.locator("#repo-table tbody tr:visible").count() == count
            page.locator("#audit").evaluate("element => element.open = false")
            page.evaluate("history.replaceState(null, '', location.pathname); window.scrollTo(0, 0)")
            assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
            if args.screenshots:
                page.screenshot(path=str(args.screenshots / "desktop.png"), full_page=True)
                page.screenshot(path=str(args.screenshots / "desktop-top.png"))
            page.set_viewport_size({"width": 390, "height": 844})
            assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
            if args.screenshots:
                page.screenshot(path=str(args.screenshots / "mobile.png"), full_page=True)
                page.screenshot(path=str(args.screenshots / "mobile-top.png"))
            assert not external, external
            assert not errors, errors
            print(f"PASS: offline rendering, {count} checkout rows, all three agent date commands, citation reveal, repository search, desktop/mobile overflow, no external requests or browser errors.")
        finally:
            browser.close()


if __name__ == "__main__":
    main()
