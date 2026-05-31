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
            with mock.patch(
                "ai_fitness_cli.cli.get_json",
                return_value={"user_id": "u", "display_name": "Bernard"},
            ):
                result = cli.main(
                    [
                        "login",
                        "--api-url",
                        "https://api.example.com/",
                        "--api-key",
                        " afb_agent_secret-with-long-value \n",
                        "--config-file",
                        str(config_file),
                    ]
                )

            self.assertEqual(result, 0)
            payload = json.loads(config_file.read_text())
            self.assertEqual(payload["api_url"], "https://api.example.com")
            self.assertEqual(payload["api_key"], "afb_agent_secret-with-long-value")
            mode = stat.S_IMODE(config_file.stat().st_mode)
            self.assertEqual(mode, stat.S_IRUSR | stat.S_IWUSR)

    def test_login_defaults_api_url_and_prompts_for_key(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            config_file = Path(temp_dir) / "config.json"
            with mock.patch("ai_fitness_cli.cli.getpass.getpass", return_value="afb_agent_prompted"), mock.patch(
                "ai_fitness_cli.cli.get_json",
                return_value={"user_id": "u"},
            ) as get_json:
                result = cli.main(["login", "--config-file", str(config_file)])

            self.assertEqual(result, 0)
            self.assertEqual(json.loads(config_file.read_text())["api_url"], cli.DEFAULT_API_URL)
            get_json.assert_called_once_with(f"{cli.DEFAULT_API_URL}/v1/agent/me", "afb_agent_prompted")

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

    def test_doctor_reports_config_source(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            config_file = Path(temp_dir) / "config.json"
            config_file.write_text(
                json.dumps(
                    {
                        "api_url": "https://api.example.com",
                        "api_key": "afb_agent_secret",
                    }
                )
            )
            with mock.patch.dict(os.environ, {cli.CONFIG_ENV: str(config_file)}, clear=False), mock.patch.dict(
                os.environ,
                {
                    cli.API_URL_ENV: "",
                    cli.API_KEY_ENV: "",
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
            ):
                result = cli.main(["doctor", "--json"])

            self.assertEqual(result, 0)

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

    def test_meals_save_accepts_shared_file_alias(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            meal_file = Path(temp_dir) / "meal.json"
            meal_file.write_text('{"meal_type": "lunch"}')
            with mock.patch.dict(
                os.environ,
                {
                    cli.API_URL_ENV: "https://api.example.com",
                    cli.API_KEY_ENV: "afb_agent_secret",
                },
                clear=False,
            ), mock.patch(
                "ai_fitness_cli.cli.post_json",
                return_value={"exit_code": 0, "stdout": ""},
            ) as post_json:
                result = cli.main(["meals", "save", "--file", str(meal_file), "--json"])

        self.assertEqual(result, 0)
        _, _, payload = post_json.call_args.args
        self.assertEqual(payload["command"], "meals.save")
        self.assertEqual(payload["args"]["meal_json"], '{"meal_type": "lunch"}')
        self.assertIsNone(payload["args"]["meal_file"])

    def test_meals_update_accepts_shared_file_alias(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            meal_file = Path(temp_dir) / "meal.json"
            meal_file.write_text('{"status": "confirmed"}')
            with mock.patch.dict(
                os.environ,
                {
                    cli.API_URL_ENV: "https://api.example.com",
                    cli.API_KEY_ENV: "afb_agent_secret",
                },
                clear=False,
            ), mock.patch(
                "ai_fitness_cli.cli.post_json",
                return_value={"exit_code": 0, "stdout": ""},
            ) as post_json:
                result = cli.main(
                    ["meals", "update", "--meal-id", "meal-1", "--file", str(meal_file), "--json"]
                )

        self.assertEqual(result, 0)
        _, _, payload = post_json.call_args.args
        self.assertEqual(payload["command"], "meals.update")
        self.assertEqual(payload["args"]["meal_update_json"], '{"status": "confirmed"}')
        self.assertIsNone(payload["args"]["meal_update_file"])

    def test_remote_error_formats_structured_backend_validation_details(self) -> None:
        body = json.dumps(
            {
                "detail": {
                    "message": "agent command validation failed",
                    "errors": [
                        {
                            "loc": ["args", "meal_json", "name"],
                            "message": (
                                "Found unsupported key 'name' at meal level; "
                                "did you mean 'meal_type'?"
                            ),
                            "suggestion": "meal_type",
                        }
                    ],
                }
            }
        )

        self.assertEqual(
            cli.format_remote_error(400, body),
            "remote API returned HTTP 400: agent command validation failed\n"
            "- args.meal_json.name: Found unsupported key 'name' at meal level; "
            "did you mean 'meal_type'?",
        )

    def test_remote_error_keeps_plain_backend_detail_readable(self) -> None:
        body = json.dumps({"detail": "unknown remote CLI command: wat"})

        self.assertEqual(
            cli.format_remote_error(400, body),
            "remote API returned HTTP 400: unknown remote CLI command: wat",
        )

    def test_admin_commands_are_not_registered(self) -> None:
        self.assertEqual(cli.main(["admin"]), 2)

    def test_skills_list_reports_bundled_skills(self) -> None:
        with mock.patch("sys.stdout") as stdout:
            result = cli.main(["skills", "list", "--json"])

        self.assertEqual(result, 0)
        output = "".join(call.args[0] for call in stdout.write.call_args_list)
        payload = json.loads(output)
        names = {skill["name"] for skill in payload["skills"]}
        self.assertIn("ai-fitness-buddy-cli", names)
        self.assertIn("fitness-program-design", names)
        self.assertIn("meal-logging", names)

    def test_skills_show_prints_skill(self) -> None:
        with mock.patch("sys.stdout") as stdout:
            result = cli.main(["skills", "show", "meal-logging"])

        self.assertEqual(result, 0)
        output = "".join(call.args[0] for call in stdout.write.call_args_list)
        self.assertIn("name: meal-logging", output)
        self.assertIn("Use this skill", output)

    def test_skills_export_copies_to_destination(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            result = cli.main(["skills", "export", "--skill", "meal-logging", "--dest", temp_dir])

            skill_file = Path(temp_dir) / "meal-logging" / "SKILL.md"
            self.assertEqual(result, 0)
            self.assertTrue(skill_file.exists())
            self.assertIn("Use this skill", skill_file.read_text())

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

    def test_hermes_setup_can_reuse_login_config(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            config_file = Path(temp_dir) / "config.json"
            memory_file = Path(temp_dir) / "USER.md"
            config_file.write_text(
                json.dumps(
                    {
                        "api_url": "https://api.example.com",
                        "api_key": "afb_agent_secret",
                    }
                )
            )
            with mock.patch("ai_fitness_cli.hermes_setup.get_json", return_value={"user_id": "u"}):
                result = cli.main(
                    [
                        "hermes",
                        "setup",
                        "--config-file",
                        str(config_file),
                        "--memory-file",
                        str(memory_file),
                        "--skip-enable-terminal",
                    ]
                )

            self.assertEqual(result, 0)
            self.assertEqual(json.loads(config_file.read_text())["api_key"], "afb_agent_secret")
            self.assertIn("fitness doctor", memory_file.read_text())


if __name__ == "__main__":
    unittest.main()
