"""Menucontroles met nagebootste invoer en uitsluitend tijdelijke doelen."""

from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import create_project as generator


class InteractiveMenuTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.output = self.root / "nieuwe projecten"
        default = patch.object(generator, "DEFAULT_OUTPUT", self.output)
        default.start()
        self.addCleanup(default.stop)

    def run_menu(self, answers):
        output, error = StringIO(), StringIO()
        with patch("builtins.input", side_effect=answers), redirect_stdout(output), redirect_stderr(error):
            result = generator.main([])
        return result, output.getvalue(), error.getvalue()

    def test_all_four_types_create_only_after_confirmation(self):
        for choice, project_type in generator.PROJECT_TYPES.items():
            with self.subTest(project_type=project_type):
                name = f"demo-{project_type}"
                destination = self.output / name
                answers = iter([choice, name, "", "ja"])

                def answer(prompt):
                    self.assertFalse(destination.exists(), "Er is vóór bevestiging geschreven")
                    if len(history) == 3:
                        self.assertIn("Aanmaken?", prompt)
                        self.assertIn(str(destination), text.getvalue())
                        self.assertIn(f"Type: {project_type}", text.getvalue())
                    history.append(prompt)
                    return next(answers)

                history = []
                text = StringIO()
                with patch("builtins.input", side_effect=answer), redirect_stdout(text):
                    self.assertEqual(generator.main([]), 0)
                self.assertTrue((destination / "README.md").is_file())
                self.assertIn(str(destination), text.getvalue())
                self.assertFalse((destination / ".git").exists())
                for path in destination.rglob("*"):
                    if path.is_file():
                        content = path.read_text(encoding="utf-8")
                        self.assertNotIn("PROJECT_NAME", content)
                        self.assertNotIn("project_package", content)

    def test_cancel_and_interrupt_at_every_input_stage(self):
        prefixes = ([], ["1"], ["1", "demo-app"], ["1", "demo-app", ""])
        for prefix in prefixes:
            for ending in ("q", "annuleren", EOFError(), KeyboardInterrupt()):
                with self.subTest(stage=len(prefix), ending=type(ending).__name__):
                    with patch.object(generator, "create_project") as create:
                        result, text, _ = self.run_menu([*prefix, ending])
                    self.assertEqual(result, 0)
                    self.assertIn("Geannuleerd", text)
                    create.assert_not_called()
                    self.assertFalse(self.output.exists())

    def test_blank_or_no_confirmation_does_not_write(self):
        for response in ("", "nee", "n"):
            with self.subTest(response=response):
                self.assertEqual(self.run_menu(["1", "demo-app", "", response])[0], 0)
                self.assertFalse(self.output.exists())

    def test_invalid_selection_and_names_are_retried(self):
        result, text, _ = self.run_menu([
            "9", "python", "../buiten", "class", "Naam met spaties", "goede-naam", "", "JA",
        ])
        self.assertEqual(result, 0)
        self.assertIn("Kies 1, 2, 3 of 4", text)
        self.assertEqual(text.count("Ongeldige naam"), 3)
        self.assertTrue((self.output / "goede-naam/src/goede_naam").is_dir())

    def test_ambiguous_confirmation_is_not_approval(self):
        result, text, _ = self.run_menu(["1", "demo-app", "", "yes", "nee"])
        self.assertEqual(result, 0)
        self.assertIn("Typ ja om aan te maken", text)
        self.assertFalse(self.output.exists())

    def test_existing_target_is_preserved_and_another_parent_can_be_chosen(self):
        existing = self.output / "demo-app"
        existing.mkdir(parents=True)
        marker = existing / "notitie.txt"
        marker.write_bytes(b"fictief")
        new_parent = self.root / "ander doel"
        result, text, _ = self.run_menu(["1", "demo-app", "", str(new_parent), "ja"])
        self.assertEqual(result, 0)
        self.assertIn("Ongeldig doel", text)
        self.assertEqual(marker.read_bytes(), b"fictief")
        self.assertTrue((new_parent / "demo-app").is_dir())

    def test_file_as_parent_is_rejected_without_creating_other_directories(self):
        file = self.root / "bestand"
        file.write_bytes(b"behouden")
        result, text, _ = self.run_menu(["1", "demo-app", str(file / "submap"), "q"])
        self.assertEqual(result, 0)
        self.assertIn("Ongeldig doel", text)
        self.assertEqual(file.read_bytes(), b"behouden")

    def test_target_created_after_preview_is_still_refused(self):
        target = self.output / "demo-app"
        answers = iter(["1", "demo-app", ""])

        def answer(prompt):
            if prompt.startswith("Aanmaken?"):
                target.mkdir(parents=True)
                (target / "behouden.txt").write_bytes(b"fictief")
                return "ja"
            return next(answers)

        with patch("builtins.input", side_effect=answer), redirect_stdout(StringIO()), redirect_stderr(StringIO()):
            self.assertEqual(generator.main([]), 1)
        self.assertEqual([p.name for p in target.iterdir()], ["behouden.txt"])

    def test_missing_template_fails_before_confirmation_or_writes(self):
        with patch.object(generator, "WEB_TEMPLATE_DIR", self.root / "ontbreekt"):
            result, _, error = self.run_menu(["2", "demo-app"])
        self.assertEqual(result, 1)
        self.assertIn("GENERATOR_FAILED", error)
        self.assertFalse(self.output.exists())

    def test_existing_cli_never_prompts_for_any_type(self):
        for project_type in generator.PROJECT_TYPES.values():
            name = f"cli-{project_type}"
            with self.subTest(project_type=project_type), patch("builtins.input", side_effect=AssertionError("Geen menu")):
                with redirect_stdout(StringIO()):
                    result = generator.main([name, "--type", project_type, "--output", str(self.output)])
                self.assertEqual(result, 0)
                self.assertTrue((self.output / name / "README.md").is_file())

    def test_partial_cli_is_an_argument_error_and_does_not_start_menu(self):
        with patch("builtins.input", side_effect=AssertionError("Geen menu")), redirect_stderr(StringIO()):
            with self.assertRaises(SystemExit) as error:
                generator.main(["--type", "python"])
        self.assertEqual(error.exception.code, 2)
        self.assertFalse(self.output.exists())


if __name__ == "__main__":
    unittest.main()
