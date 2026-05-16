from __future__ import annotations

import json
import os
import stat
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from ai_fitness_cli import cli
from ai_fitness_cli import hermes_setup


class CliTests(unittest.TestCase):
    def test_normalize_api_url_strips_v1(self) -> None:
        self.assertEqual(
            cli.normalize_api_url("https://api.example.com/v1"),
            "https://api.example.com",
        )

    def test_login_writes_locked_config(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            config_file = Path(temp_dir) / "config.json"
            with mock.patch("ai_fitness_cli.cli.get_json", return_value={"user_id": "u"}):
                result = cli.main(
                    [
                        "login",
                        "--api-url",
                        "https://api.example.com",
                        "--api-key",
                        "afb_agent_secret",
                        "--config-file",
                        str(config_file),
                    ]
                )

            self.assertEqual(result, 0)
            payload = json.loads(config_file.read_text())
            self.assertEqual(payload["api_url"], "https://api.example.com")
            self.assertEqual(payload["api_key"], "afb_agent_secret")
            mode = stat.S_IMODE(config_file.stat().st_mode)
            self.assertEqual(mode, stat.S_IRUSR | stat.S_IWUSR)

    def test_doctor_uses_env_credentials(self) -> None:
        with mock.patch.dict(
            os.environ,
            {
                cli.API_URL_ENV: "https://api.example.com",
                cli.API_KEY_ENV: "afb_agent_secret",
            },
            clear=False,
        ), mock.patch(
            "ai_fitness_cli.cli.get_json",
            return_value={
                "user_id": "user-1",
                "display_name": "Alice",
                "timezone": "Asia/Hong_Kong",
                "scope": "agent",
            },
        ) as get_json:
            result = cli.main(["doctor"])

        self.assertEqual(result, 0)
        get_json.assert_called_once_with("https://api.example.com/v1/agent/me", "afb_agent_secret")

    def test_remote_command_payload(self) -> None:
        with mock.patch.dict(
            os.environ,
            {
                cli.API_URL_ENV: "https://api.example.com",
                cli.API_KEY_ENV: "afb_agent_secret",
            },
            clear=False,
        ), mock.patch(
            "ai_fitness_cli.cli.post_json",
            return_value={"exit_code": 0, "stdout": "ok\n"},
        ) as post_json:
            result = cli.main(["context", "brief", "--as-of", "2026-05-16", "--json"])

        self.assertEqual(result, 0)
        post_json.assert_called_once()
        _, _, payload = post_json.call_args.args
        self.assertEqual(payload["command"], "context.brief")
        self.assertEqual(payload["args"]["as_of"], "2026-05-16")
        self.assertEqual(payload["args"]["format"], "json")

    def test_admin_commands_are_not_registered(self) -> None:
        self.assertEqual(cli.main(["admin"]), 2)

    def test_hermes_setup_writes_config_and_memory(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            config_file = Path(temp_dir) / "config.json"
            memory_file = Path(temp_dir) / "USER.md"
            with mock.patch("ai_fitness_cli.hermes_setup.get_json", return_value={"user_id": "u"}):
                result = hermes_setup.main(
                    [
                        "--api-url",
                        "https://api.example.com",
                        "--api-key",
                        "afb_agent_secret",
                        "--config-file",
                        str(config_file),
                        "--memory-file",
                        str(memory_file),
                        "--skip-enable-terminal",
                    ]
                )

            self.assertEqual(result, 0)
            self.assertEqual(json.loads(config_file.read_text())["api_key"], "afb_agent_secret")
            self.assertIn("fitness context brief", memory_file.read_text())

    def test_hermes_setup_is_available_from_main_cli(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            config_file = Path(temp_dir) / "config.json"
            memory_file = Path(temp_dir) / "USER.md"
            with mock.patch("ai_fitness_cli.hermes_setup.get_json", return_value={"user_id": "u"}):
                result = cli.main(
                    [
                        "hermes",
                        "setup",
                        "--api-url",
                        "https://api.example.com",
                        "--api-key",
                        "afb_agent_secret",
                        "--config-file",
                        str(config_file),
                        "--memory-file",
                        str(memory_file),
                        "--skip-enable-terminal",
                    ]
                )

            self.assertEqual(result, 0)
            self.assertEqual(json.loads(config_file.read_text())["api_url"], "https://api.example.com")
            self.assertIn("fitness doctor", memory_file.read_text())


if __name__ == "__main__":
    unittest.main()
