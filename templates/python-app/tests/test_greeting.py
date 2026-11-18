"""Tests die rechtstreeks vanuit de projectmap kunnen draaien."""

from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
import sys
import unittest

# unittest discover importeert dit bestand voordat de package nodig is.
# Gebruik het bestandspad, zodat dit niet afhangt van de huidige werkmap.
SRC_PATH = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC_PATH))

from project_package.greeting import greet
from project_package.__main__ import main


class GreetingTests(unittest.TestCase):
    def test_greets_example_name(self):
        self.assertEqual(greet("Voorbeeld"), "Hallo, Voorbeeld!")

    def test_strips_surrounding_whitespace(self):
        self.assertEqual(greet("  Voorbeeld\n"), "Hallo, Voorbeeld!")

    def test_rejects_empty_or_whitespace_name(self):
        for name in ("", " ", "\t\n"):
            with self.subTest(name=name):
                with self.assertRaisesRegex(ValueError, "naam mag niet leeg"):
                    greet(name)

    def test_main_prints_example_greeting(self):
        output = StringIO()
        with redirect_stdout(output):
            main()
        self.assertEqual(output.getvalue(), "Hallo, Voorbeeld!\n")


if __name__ == "__main__":
    unittest.main()
