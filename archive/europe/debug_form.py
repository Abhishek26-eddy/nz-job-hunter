#!/usr/bin/env python3
"""Debug a single ATS application page and dump the form HTML."""

import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

URL = sys.argv[1] if len(sys.argv) > 1 else "https://job-boards.greenhouse.io/doctolib/jobs/7730606003"
OUT = Path("/tmp/form_debug")
OUT.mkdir(exist_ok=True)

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1280, "height": 900})
    print(f"Loading {URL}")
    page.goto(URL, wait_until="networkidle", timeout=45000)
    page.wait_for_timeout(2000)

    # Click any visible Apply link/button to reveal the form
    for sel in ("a[href*='apply']", "button:has-text('Apply')", "a:has-text('Apply')"):
        try:
            link = page.locator(sel).first
            if link.is_visible(timeout=2000):
                print(f"Clicking {sel}")
                link.click()
                page.wait_for_load_state("networkidle", timeout=15000)
                page.wait_for_timeout(2000)
                break
        except Exception as exc:
            print(f"  {sel}: {exc}")

    html = page.content()
    (OUT / "page.html").write_text(html, encoding="utf-8")
    page.screenshot(path=str(OUT / "screenshot.png"), full_page=True)

    # Find all file inputs, submit buttons, visible forms
    forms = page.locator("form").all()
    print(f"Forms found: {len(forms)}")
    for i, form in enumerate(forms):
        try:
            inner = form.inner_html()
            (OUT / f"form_{i}.html").write_text(inner, encoding="utf-8")
            print(f"  Form {i} saved")
        except Exception as exc:
            print(f"  Form {i} error: {exc}")

    # Also save specific form fields
    for part in ("resume", "cover", "submit", "first_name", "last_name", "email", "phone"):
        try:
            if page.locator(f"#{part}").count():
                (OUT / f"field_{part}.html").write_text(page.locator(f"#{part}").first.inner_html())
                print(f"  field {part} saved")
        except Exception as exc:
            pass

    print(f"Debug files written to {OUT}")
    browser.close()
