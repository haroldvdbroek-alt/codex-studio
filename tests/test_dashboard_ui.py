"""Gedrag van lokale JavaScript-interface zonder browser of netwerk testen."""

from pathlib import Path
from html.parser import HTMLParser
import re
import shutil
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
NODE = shutil.which("node")


class DashboardFrontendTests(unittest.TestCase):
    def test_actual_html_contains_javascript_targets_and_no_inline_handlers(self):
        ids = []
        class Page(HTMLParser):
            def handle_starttag(inner, tag, attributes):
                for name, value in attributes:
                    self.assertFalse(name.startswith("on"), "Geen inline-eventhandlers")
                    if name == "id":
                        ids.append(value)
        Page().feed((ROOT / "dashboard/index.html").read_text(encoding="utf-8"))
        source = (ROOT / "dashboard/app.js").read_text(encoding="utf-8")
        required = set(re.findall(r'byId\("([^"\n]+)"\)', source)) | {"total", "attention", "updates"}
        self.assertTrue(required.issubset(set(ids)), required - set(ids))
        self.assertEqual(len(ids), len(set(ids)))

    @unittest.skipUnless(NODE, "Node.js vereist voor JavaScript-gedragstests; niets geïnstalleerd")
    def test_dashboard_interaction_and_safe_text_rendering(self):
        result = subprocess.run([NODE, "--test", str(ROOT / "tests/dashboard-ui.test.cjs")],
                                cwd=ROOT, shell=False, capture_output=True, text=True,
                                encoding="utf-8", errors="replace", timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
