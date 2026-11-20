"""Controleer het HTML-contract zonder externe Python-pakketten."""

from html.parser import HTMLParser
from pathlib import Path
import unittest
from urllib.parse import urlsplit


ROOT = Path(__file__).resolve().parents[1]


class PageParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.elements = []

    def handle_starttag(self, tag, attrs):
        self.elements.append((tag, dict(attrs)))


class PageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.page = PageParser()
        cls.html = (ROOT / "public/index.html").read_text(encoding="utf-8")
        cls.page.feed(cls.html)

    def test_page_has_language_viewport_and_heading(self):
        self.assertTrue(any(tag == "html" and attrs.get("lang") == "nl"
                            for tag, attrs in self.page.elements))
        self.assertTrue(any(tag == "meta" and attrs.get("name") == "viewport"
                            for tag, attrs in self.page.elements))
        self.assertEqual(sum(tag == "h1" for tag, _ in self.page.elements), 1)
        self.assertIn("<title>", self.html)

    def test_counter_contract_and_unique_ids(self):
        ids = [attrs["id"] for _, attrs in self.page.elements if "id" in attrs]
        self.assertEqual(len(ids), len(set(ids)))
        for name in ("count", "increment", "reset"):
            self.assertIn(name, ids)
        for name in ("increment", "reset"):
            self.assertTrue(any(tag == "button" and attrs.get("id") == name
                                and attrs.get("type") == "button"
                                for tag, attrs in self.page.elements))
        self.assertTrue(any(attrs.get("aria-live") == "polite"
                            for _, attrs in self.page.elements))

    def test_assets_are_local_existing_and_loaded(self):
        references = []
        for tag, attrs in self.page.elements:
            if tag == "script":
                self.assertIn("defer", attrs)
                self.assertIn("src", attrs)
                references.append(attrs["src"])
            if tag == "link" and attrs.get("rel") == "stylesheet":
                references.append(attrs["href"])
        self.assertEqual(set(references), {"styles.css", "app.js"})
        for reference in references:
            url = urlsplit(reference)
            self.assertFalse(url.scheme or url.netloc)
            target = (ROOT / "public" / url.path).resolve()
            self.assertTrue(target.is_relative_to((ROOT / "public").resolve()))
            self.assertTrue(target.is_file())


if __name__ == "__main__":
    unittest.main()
