"""Playwright helpers. Browser tests are skipped (not failed) when Playwright isn't installed:
python3.12 -m venv .venv && .venv/bin/pip install playwright==1.64.0"""
import unittest

try:
    from playwright.sync_api import sync_playwright
    HAVE_PLAYWRIGHT = True
except ImportError:  # pragma: no cover
    sync_playwright = None
    HAVE_PLAYWRIGHT = False

needs_browser = unittest.skipUnless(HAVE_PLAYWRIGHT, "Playwright not installed (see tests/README.md)")


class Page:
    """A Chromium page that records page errors and console errors."""

    def __init__(self, width=1600, height=950):
        self.size = {"width": width, "height": height}

    def __enter__(self):
        self.pw = sync_playwright().start()
        self.browser = self.pw.chromium.launch()
        self.page = self.browser.new_page(viewport=self.size)
        self.errors = []
        self.page.on("pageerror", lambda e: self.errors.append(f"pageerror: {e}"))
        self.page.on("console", lambda m: m.type == "error" and self.errors.append(f"console error: {m.text}"))
        return self

    def __exit__(self, *exc):
        self.browser.close()
        self.pw.stop()
