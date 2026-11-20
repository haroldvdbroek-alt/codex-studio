"""Offline tests met fictieve configuratie en geblokkeerde netwerktoegang."""

from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path
import socket
import sys
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from project_package import config
from project_package.__main__ import main
from project_package.client import MockClient
from project_package.config import Settings, load_settings
from project_package.service import generate_reply


class OfflineTests(unittest.TestCase):
    def setUp(self):
        # Ook een toekomstige onbedoelde netwerkverbinding moet de test laten falen.
        for name in ("socket", "create_connection", "getaddrinfo"):
            guard = patch.object(socket, name, side_effect=AssertionError("Netwerk verboden in tests"))
            guard.start()
            self.addCleanup(guard.stop)

    def test_defaults_need_no_key(self):
        settings = load_settings({})
        self.assertEqual(settings.mode, "mock")
        self.assertEqual(settings.model, "demo-model")
        self.assertIsNone(settings.api_key)

    def test_explicit_fictitious_configuration(self):
        settings = load_settings({"AI_MODE": " mock ", "AI_MODEL": " demo-test ",
                                  "AI_API_KEY": " fictieve-testsleutel "})
        self.assertEqual(settings.model, "demo-test")
        self.assertEqual(settings.api_key, "fictieve-testsleutel")

    def test_environment_read_is_isolated_from_real_environment(self):
        with patch.object(config.os, "environ", {"AI_MODEL": "fictief-model"}):
            self.assertEqual(load_settings().model, "fictief-model")
            self.assertIsNone(load_settings().api_key)

    def test_secret_is_hidden_from_representation(self):
        settings = load_settings({"AI_API_KEY": "fictieve-testsleutel"})
        self.assertNotIn("fictieve-testsleutel", repr(settings))

    def test_empty_key_is_optional(self):
        self.assertIsNone(load_settings({"AI_API_KEY": "  "}).api_key)

    def test_invalid_configuration_does_not_echo_values(self):
        for environ in ({"AI_MODE": "fictieve-geheime-waarde"}, {"AI_MODEL": " "}):
            with self.subTest(environ=environ), self.assertRaises(ValueError) as error:
                load_settings(environ)
            self.assertNotIn("fictieve-geheime-waarde", str(error.exception))

    def test_mock_returns_deterministic_response_without_key(self):
        self.assertEqual(MockClient().complete("Hallo", model="demo"), "[demo:demo] Hallo")
        self.assertEqual(generate_reply(" Hallo ", load_settings({})), "[demo:demo-model] Hallo")

    def test_empty_prompt_is_rejected_without_calling_client(self):
        client = Mock()
        for prompt in ("", " \t\n"):
            with self.subTest(prompt=prompt), self.assertRaises(ValueError):
                generate_reply(prompt, Settings(), client)
        client.complete.assert_not_called()

    def test_client_can_be_replaced_with_a_test_double(self):
        client = Mock()
        client.complete.return_value = "Fictief antwoord"
        self.assertEqual(generate_reply(" Vraag ", Settings(model="demo-test"), client),
                         "Fictief antwoord")
        client.complete.assert_called_once_with("Vraag", model="demo-test")

    def test_non_mock_mode_cannot_enable_a_provider(self):
        with self.assertRaises(ValueError):
            generate_reply("Hallo", Settings(mode="live"))

    def test_app_runs_offline_and_does_not_print_key(self):
        output = StringIO()
        with redirect_stdout(output):
            result = main({"AI_API_KEY": "fictieve-testsleutel"})
        self.assertEqual(result, 0)
        self.assertEqual(output.getvalue(), "[demo:demo-model] Geef een korte begroeting.\n")
        self.assertNotIn("fictieve-testsleutel", output.getvalue())

    def test_app_reports_configuration_errors(self):
        error = StringIO()
        with redirect_stderr(error):
            result = main({"AI_MODE": "fictieve-geheime-waarde"})
        self.assertEqual(result, 1)
        self.assertIn("Configuratiefout", error.getvalue())
        self.assertNotIn("fictieve-geheime-waarde", error.getvalue())

    def test_network_guard_is_active(self):
        with self.assertRaisesRegex(AssertionError, "Netwerk verboden"):
            socket.create_connection(("example.invalid", 443))


if __name__ == "__main__":
    unittest.main()
