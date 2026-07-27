from __future__ import annotations

import argparse
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
    def test_default_api_url_uses_ascent_production(self) -> None:
        self.assertEqual(
            cli.DEFAULT_API_URL,
            "https://api.ascent-ai-fitness-coach.com",
        )

    def test_normalize_api_url_strips_v1(self) -> None:
        self.assertEqual(
            cli.normalize_api_url("https://api.example.com/v1"),
            "https://api.example.com",
        )

    def test_normalize_api_url_migrates_legacy_production_host(self) -> None:
        self.assertEqual(
            cli.normalize_api_url("https://api.bernardtktsangfitness.com/v1"),
            cli.DEFAULT_API_URL,
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

    def test_timezone_override_is_forwarded_to_remote_command(self) -> None:
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
            result = cli.main([
                "meals",
                "list",
                "--start",
                "2026-06-01",
                "--end",
                "2026-06-06",
                "--timezone",
                "Asia/Hong_Kong",
            ])

        self.assertEqual(result, 0)
        _, _, payload = post_json.call_args.args
        self.assertEqual(payload["command"], "meals.list")
        self.assertEqual(payload["args"]["timezone"], "Asia/Hong_Kong")

    def test_meals_save_accepts_shared_file_alias(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            meal_file = Path(temp_dir) / "meal.json"
            meal_file.write_text('{"meal_type": "lunch", "items": [{"name": "Lunch estimate", "calories": 600, "protein_g": 30, "carbs_g": 60, "fat_g": 20}]}')
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
        self.assertEqual(
            payload["args"]["meal_json"],
            '{"meal_type": "lunch", "items": [{"name": "Lunch estimate", "calories": 600, "protein_g": 30, "carbs_g": 60, "fat_g": 20}]}',
        )
        self.assertIsNone(payload["args"]["meal_file"])

    def test_meals_update_accepts_shared_file_alias(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            meal_file = Path(temp_dir) / "meal.json"
            meal_file.write_text('{"notes": "corrected estimate"}')
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
        self.assertEqual(payload["args"]["meal_update_json"], '{"notes": "corrected estimate"}')
        self.assertIsNone(payload["args"]["meal_update_file"])

    def test_workouts_save_maps_json_body_to_remote_command(self) -> None:
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
            result = cli.main([
                "workouts",
                "save",
                "--workout-json",
                '{"workout_type": "strength_training", "start_time": "2026-06-12T18:00:00", "end_time": "2026-06-12T18:55:00"}',
                "--timezone",
                "Asia/Hong_Kong",
            ])

        self.assertEqual(result, 0)
        _, _, payload = post_json.call_args.args
        self.assertEqual(payload["command"], "workouts.save")
        self.assertEqual(
            payload["args"]["workout_json"],
            '{"workout_type": "strength_training", "start_time": "2026-06-12T18:00:00", "end_time": "2026-06-12T18:55:00"}',
        )
        self.assertEqual(payload["args"]["timezone"], "Asia/Hong_Kong")

    def test_workouts_save_accepts_shared_file_alias(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workout_file = Path(temp_dir) / "workout.json"
            workout_file.write_text(
                '{"workout_type": "running", "start_time": "2026-06-12T18:00:00", "end_time": "2026-06-12T18:30:00"}'
            )
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
                result = cli.main(["workouts", "save", "--file", str(workout_file), "--json"])

        self.assertEqual(result, 0)
        _, _, payload = post_json.call_args.args
        self.assertEqual(payload["command"], "workouts.save")
        self.assertEqual(
            payload["args"]["workout_json"],
            '{"workout_type": "running", "start_time": "2026-06-12T18:00:00", "end_time": "2026-06-12T18:30:00"}',
        )
        self.assertIsNone(payload["args"]["workout_file"])

    def test_workout_write_commands_forward_json_payloads(self) -> None:
        cases = [
            (
                [
                    "workouts",
                    "save",
                    "--workout-json",
                    '{"workout_type":"running","start_time":"2026-06-01T07:00:00","end_time":"2026-06-01T08:00:00"}',
                    "--timezone",
                    "Asia/Hong_Kong",
                ],
                "workouts.save",
                "workout_json",
            ),
            (
                [
                    "workouts",
                    "update",
                    "--workout-id",
                    "00000000-0000-0000-0000-000000000001",
                    "--workout-update-json",
                    '{"notes":"easy effort"}',
                ],
                "workouts.update",
                "workout_update_json",
            ),
            (
                [
                    "workouts",
                    "delete",
                    "--workout-id",
                    "00000000-0000-0000-0000-000000000001",
                ],
                "workouts.delete",
                None,
            ),
        ]
        for argv, command, json_key in cases:
            with self.subTest(command=command), mock.patch.dict(
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
                result = cli.main(argv)

            self.assertEqual(result, 0)
            _, _, payload = post_json.call_args.args
            self.assertEqual(payload["command"], command)
            if json_key:
                self.assertIn(json_key, payload["args"])

    def test_new_read_and_programme_commands_forward_remote_contracts(self) -> None:
        cases = [
            (
                ["context", "trend", "--as-of", "2026-06-30", "--weeks", "6"],
                "context.trend",
                {"as_of": "2026-06-30", "weeks": 6},
            ),
            (
                ["nutrition", "lookup", "char siu rice", "--portion-hint", "one plate"],
                "nutrition.lookup",
                {"query": "char siu rice", "portion_hint": "one plate"},
            ),
            (["programme", "list", "--limit", "10"], "programme.list", {"limit": 10}),
            (
                [
                    "programme",
                    "activate",
                    "--projection-id",
                    "00000000-0000-0000-0000-000000000001",
                ],
                "programme.activate",
                {"projection_id": "00000000-0000-0000-0000-000000000001"},
            ),
            (["dashboard", "metrics", "show"], "dashboard.metrics.show", {}),
        ]
        for argv, command, expected in cases:
            with self.subTest(command=command), mock.patch.dict(
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
                result = cli.main(argv)

            self.assertEqual(result, 0)
            _, _, payload = post_json.call_args.args
            self.assertEqual(payload["command"], command)
            for key, value in expected.items():
                self.assertEqual(payload["args"][key], value)

    def test_foods_search_remote_payload_defaults_and_filters(self) -> None:
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
                [
                    "foods",
                    "search",
                    "soba",
                    "--limit",
                    "12",
                    "--entry-limit",
                    "2",
                    "--start",
                    "2026-05-01",
                    "--end",
                    "2026-06-02",
                    "--meal-type",
                    "lunch",
                    "--json",
                ]
            )

        self.assertEqual(result, 0)
        _, _, payload = post_json.call_args.args
        self.assertEqual(payload["command"], "foods.search")
        self.assertEqual(payload["args"]["query"], "soba")
        self.assertEqual(payload["args"]["limit"], 12)
        self.assertEqual(payload["args"]["entry_limit"], 2)
        self.assertEqual(payload["args"]["start"], "2026-05-01")
        self.assertEqual(payload["args"]["end"], "2026-06-02")
        self.assertEqual(payload["args"]["meal_type"], "lunch")
        self.assertNotIn("status", payload["args"])
        self.assertEqual(payload["args"]["format"], "json")

    def test_foods_commands_remote_payloads(self) -> None:
        cases = [
            (["foods", "list", "--json"], "foods.list", {"limit": 50}),
            (["foods", "history", "rice", "--json"], "foods.history", {"name": "rice", "limit": 20}),
            (["foods", "get", "rice", "--json"], "foods.get", {"name": "rice", "limit": 5}),
        ]
        for argv, command, expected_args in cases:
            with self.subTest(command=command), mock.patch.dict(
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
                result = cli.main(argv)

            self.assertEqual(result, 0)
            _, _, payload = post_json.call_args.args
            self.assertEqual(payload["command"], command)
            for key, value in expected_args.items():
                self.assertEqual(payload["args"][key], value)
            self.assertEqual(payload["args"]["format"], "json")

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

    def test_health_samples_command_is_not_registered(self) -> None:
        self.assertEqual(cli.main(["health", "samples"]), 2)

    def test_public_remote_command_contract_is_explicit_and_complete(self) -> None:
        def collect(parser: argparse.ArgumentParser) -> set[str]:
            commands = set()
            remote_command = parser._defaults.get("remote_command")
            if remote_command:
                commands.add(remote_command)
            for action in parser._actions:
                if isinstance(action, argparse._SubParsersAction):
                    for child in action.choices.values():
                        commands.update(collect(child))
            return commands

        expected = {
            "context.brief",
            "context.trend",
            "progress.show",
            "health.summary",
            "health.body",
            "health.catalog",
            "workouts.list",
            "workouts.save",
            "workouts.update",
            "workouts.delete",
            "sync.status",
            "profile.show",
            "profile.update",
            "meals.summary",
            "meals.list",
            "meals.save",
            "meals.update",
            "meals.delete",
            "nutrition.lookup",
            "foods.search",
            "foods.list",
            "foods.history",
            "foods.get",
            "projections.list",
            "projections.show",
            "projections.deactivate",
            "projections.delete",
            "programme.list",
            "programme.save",
            "programme.activate",
            "targets.validate",
            "targets.explain",
            "targets.phase.save",
            "targets.schedule.save",
            "targets.schedule.list",
            "targets.schedule.show",
            "targets.schedule.update",
            "targets.schedule.deactivate",
            "targets.schedule.delete",
            "targets.daily.save",
            "recommendation.write",
            "dashboard.metrics.show",
            "dashboard.metrics.set",
        }

        self.assertEqual(collect(cli.build_parser()), expected)

    def test_skills_list_reports_bundled_skills(self) -> None:
        with mock.patch("sys.stdout") as stdout:
            result = cli.main(["skills", "list", "--json"])

        self.assertEqual(result, 0)
        output = "".join(call.args[0] for call in stdout.write.call_args_list)
        payload = json.loads(output)
        names = {skill["name"] for skill in payload["skills"]}
        self.assertIn("ascent-ai-cli", names)
        self.assertIn("fitness-program-design", names)
        self.assertIn("meal-logging", names)

    def test_coaching_skill_is_bundled(self) -> None:
        with mock.patch("sys.stdout") as stdout:
            result = cli.main(["skills", "list", "--json"])

        self.assertEqual(result, 0)
        output = "".join(call.args[0] for call in stdout.write.call_args_list)
        names = {skill["name"] for skill in json.loads(output)["skills"]}
        self.assertIn("coaching-best-practices", names)

    def test_coaching_skill_documents_atomic_habits_behaviors(self) -> None:
        skill = (cli.get_skill_dir("coaching-best-practices") / "SKILL.md").read_text()

        # (a) summarize progress and encourage when on track, reusing item 40's
        # enriched brief instead of authoring a second progress summary.
        self.assertIn("fitness context brief", skill)
        self.assertIn("on track", skill.lower())
        # (b) propose habit stacking at plan setup.
        self.assertIn("habit stack", skill.lower())
        # (c) ask the user their self-chosen reward.
        self.assertIn("reward", skill.lower())
        # Reuses allowlisted commands; adds no new tool surface.
        self.assertIn("no new", skill.lower())

    def test_skills_show_prints_skill(self) -> None:
        with mock.patch("sys.stdout") as stdout:
            result = cli.main(["skills", "show", "meal-logging"])

        self.assertEqual(result, 0)
        output = "".join(call.args[0] for call in stdout.write.call_args_list)
        self.assertIn("name: meal-logging", output)
        self.assertIn("Use this skill", output)

    def test_bundled_skills_document_food_history_lookup(self) -> None:
        cli_skill = (cli.get_skill_dir("ascent-ai-cli") / "SKILL.md").read_text()
        meal_skill = (cli.get_skill_dir("meal-logging") / "SKILL.md").read_text()

        self.assertIn("fitness foods search", cli_skill)
        self.assertIn("fitness foods get", cli_skill)
        self.assertIn("fitness nutrition lookup", cli_skill)
        self.assertIn("fitness foods search", meal_skill)
        self.assertIn("fitness nutrition lookup", meal_skill)
        self.assertIn("not a generic food", meal_skill)

    def test_program_design_skill_documents_edit_in_place_programme_updates(self) -> None:
        program_skill = (cli.get_skill_dir("fitness-program-design") / "SKILL.md").read_text()

        self.assertIn("edit the\nexisting programme, phase, or schedule in place", program_skill)
        self.assertIn("Do not create another active", program_skill)
        self.assertIn("deactivate or delete the superseded", program_skill)
        self.assertIn("weekly_overrides`: flat weekly totals", program_skill)
        self.assertIn("weekday_targets`: recurring day-of-week values", program_skill)

    def test_program_design_skill_documents_durable_memory_guidance(self) -> None:
        program_skill = (cli.get_skill_dir("fitness-program-design") / "SKILL.md").read_text()

        self.assertIn("Save durable coaching context to agent memory", program_skill)
        self.assertIn("dietary restriction", program_skill)
        self.assertIn("physical limitation or injury", program_skill)
        self.assertIn("lifestyle preference", program_skill)
        self.assertIn("goal update", program_skill)
        self.assertIn("stated dislike", program_skill)
        self.assertIn("diet.vegetarian", program_skill)
        self.assertIn("injury.left-knee", program_skill)
        self.assertIn("preference.evening-workouts", program_skill)
        self.assertIn("2200-character memory budget", program_skill)

    def test_program_design_skill_documents_workout_write(self) -> None:
        program_skill = (cli.get_skill_dir("fitness-program-design") / "SKILL.md").read_text()

        self.assertIn("fitness workouts save", program_skill)
        self.assertIn("set server-side", program_skill)


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
