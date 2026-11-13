from __future__ import annotations

import argparse
import io
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
        ) as get_json, mock.patch("ai_fitness_cli.cli.post_json", return_value={"exit_code": 0, "stdout": "{}"}):
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
            ), mock.patch("ai_fitness_cli.cli.post_json", return_value={"exit_code": 0, "stdout": "{}"}):
                result = cli.main(["doctor", "--json"])

            self.assertEqual(result, 0)

    # ------------------------------------------------------------------ v2 remote commands

    def run_cli(self, argv: list[str], response: dict | None = None) -> tuple[int, dict]:
        """Run the CLI with a mocked API; return (exit code, the posted command payload)."""
        with mock.patch.dict(
            os.environ,
            {cli.API_URL_ENV: "https://api.example.com", cli.API_KEY_ENV: "afb_agent_secret"},
            clear=False,
        ), mock.patch(
            "ai_fitness_cli.cli.post_json",
            return_value=response or {"exit_code": 0, "stdout": "ok\n"},
        ) as post_json:
            result = cli.main(argv)
        if not post_json.call_args:
            return result, {}
        _, _, payload = post_json.call_args.args
        return result, payload

    def assert_command(self, argv: list[str], command: str, args: dict | None = None) -> dict:
        result, payload = self.run_cli(argv)
        self.assertEqual(result, 0, argv)
        self.assertEqual(payload["command"], command, argv)
        sent = dict(payload["args"])
        self.assertEqual(sent.pop("format"), "text", argv)
        if args is not None:
            self.assertEqual(sent, args, argv)
        return sent

    def test_remote_command_payload(self) -> None:
        result, payload = self.run_cli(["context", "brief", "--as-of", "2026-05-16", "--json"])

        self.assertEqual(result, 0)
        self.assertEqual(payload["command"], "get_context_brief")
        self.assertEqual(payload["args"], {"as_of": "2026-05-16", "format": "json"})

    def test_context_and_read_commands_map_to_v2_tools(self) -> None:
        self.assert_command(
            ["context", "brief", "--include", "goals,sync", "--week-start", "2026-06-01"],
            "get_context_brief",
            {"include": ["goals", "sync"], "week_start": "2026-06-01"},
        )
        self.assert_command(["context", "day", "--date", "2026-06-02", "--timezone", "Asia/Hong_Kong"], "get_day",
                            {"date": "2026-06-02", "timezone": "Asia/Hong_Kong"})
        self.assert_command(["context", "trend", "--weeks", "6"], "get_health_trends",
                            {"sections": ["trend"], "weeks": 6})
        self.assert_command(
            ["health", "trends", "--start", "2026-06-01", "--sections", "health,samples", "--sample-metrics", "heart_rate"],
            "get_health_trends",
            {"start": "2026-06-01", "sections": ["health", "samples"], "sample_metrics": ["heart_rate"]},
        )
        self.assert_command(["health", "summary", "--start", "2026-06-01", "--end", "2026-06-03"], "get_health_trends",
                            {"sections": ["health"], "start": "2026-06-01", "end": "2026-06-03"})
        self.assert_command(["health", "body", "--metrics", "weight_kg,body_fat_percent"], "get_health_trends",
                            {"sections": ["body"], "body_metrics": ["weight_kg", "body_fat_percent"]})
        self.assert_command(["sync", "status"], "get_context_brief", {"include": ["sync"]})
        self.assert_command(["profile", "show"], "get_context_brief", {"include": ["profile"]})
        self.assert_command(["goals", "list"], "get_context_brief", {"include": ["goals"]})
        self.assert_command(["programme", "list"], "get_context_brief", {"include": ["programmes"]})
        self.assert_command(["targets", "show", "--as-of", "2026-06-01"], "get_context_brief", {"as_of": "2026-06-01"})
        self.assert_command(["dashboard", "metrics", "show"], "get_context_brief", {"include": ["dashboard"]})

    def test_timezone_override_is_forwarded_to_remote_command(self) -> None:
        self.assert_command(
            ["meals", "list", "--date", "2026-06-06", "--timezone", "Asia/Hong_Kong"],
            "get_day",
            {"date": "2026-06-06", "timezone": "Asia/Hong_Kong"},
        )

    def test_meal_commands_map_to_v2_tools(self) -> None:
        meal = {"meal_type": "lunch", "items": [{"name": "Rice", "calories": 600}]}
        sent = self.assert_command(
            ["meals", "save", "--meal-json", json.dumps(meal), "--timezone", "Asia/Hong_Kong"], "log_meal"
        )
        self.assertEqual(sent["meal"], {**meal, "timezone": "Asia/Hong_Kong"})
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "meal.json"
            path.write_text(json.dumps(meal))
            sent = self.assert_command(["meals", "save", "--file", str(path)], "log_meal")
            self.assertEqual(sent["meal"], meal)
        self.assert_command(
            ["meals", "update", "--meal-id", "m1", "--meal-update-json", '{"title": "Lunch"}'],
            "edit_meal",
            {"meal_id": "m1", "updates": {"title": "Lunch"}},
        )
        self.assert_command(["meals", "delete", "--meal-id", "m1"], "delete_item", {"type": "meal", "id": "m1"})
        self.assert_command(["meals", "scale", "--meal-id", "m1", "--servings-scale", "1.5"], "edit_meal",
                            {"meal_id": "m1", "servings_scale": 1.5})
        self.assert_command(
            ["meals", "item-update", "--meal-id", "m1", "--item-id", "i1", "--item-changes-json", '{"calories": 123}'],
            "edit_meal",
            {"meal_id": "m1", "item_id": "i1", "item_changes": {"calories": 123}},
        )
        self.assert_command(["meals", "item-delete", "--meal-id", "m1", "--item-id", "i1"], "edit_meal",
                            {"meal_id": "m1", "item_id": "i1", "remove_item": True})
        self.assert_command(["meals", "summary", "--start", "2026-06-01"], "get_health_trends",
                            {"sections": ["nutrition"], "start": "2026-06-01"})

    def test_meals_add_builds_quick_add_log_with_title(self) -> None:
        sent = self.assert_command(
            ["meals", "add", "--title", "Shake", "--calories", "250", "--protein", "30"], "log_meal"
        )
        meal = sent["meal"]
        self.assertEqual(meal["title"], "Shake")
        self.assertEqual(meal["items"][0]["calories"], 250)
        self.assertEqual(meal["items"][0]["protein_g"], 30)

    def test_old_meal_undo_and_nutrition_commands_are_gone(self) -> None:
        for argv in (["meals", "undo", "--meal-id", "m1"], ["nutrition", "lookup", "oats"], ["progress", "show"]):
            self.assertEqual(cli.main(argv), 2, argv)

    def test_food_commands_map_to_search_foods_modes(self) -> None:
        self.assert_command(["foods", "search", "oats", "--meal-type", "lunch"], "search_foods",
                            {"mode": "history", "query": "oats", "meal_type": "lunch", "limit": 10})
        self.assert_command(["foods", "list", "--limit", "5"], "search_foods", {"mode": "frequent", "limit": 5})
        self.assert_command(["foods", "lookup", "Big Mac", "--portion-hint", "1 burger"], "search_foods",
                            {"mode": "lookup", "query": "Big Mac", "portion_hint": "1 burger"})
        for argv in (["foods", "history", "oats"], ["foods", "get", "oats"]):
            self.assertEqual(cli.main(argv), 2, argv)

    def test_workout_commands_map_to_v2_tools(self) -> None:
        workout = {"workout_type": "running", "start_time": "2026-06-12T18:00:00", "end_time": "2026-06-12T18:30:00"}
        sent = self.assert_command(["workouts", "save", "--workout-json", json.dumps(workout), "--timezone", "UTC"], "log_workout")
        self.assertEqual(sent["workout"], {**workout, "timezone": "UTC"})
        self.assert_command(
            ["workouts", "update", "--workout-id", "w1", "--changes-json", '{"workout_type": "cycling"}'],
            "log_workout",
            {"workout_id": "w1", "changes": {"workout_type": "cycling"}},
        )
        self.assert_command(["workouts", "delete", "--workout-id", "w1"], "delete_item", {"type": "workout", "id": "w1"})
        self.assert_command(["workouts", "list", "--start", "2026-06-01", "--end", "2026-06-07"], "get_health_trends",
                            {"sections": ["workouts"], "start": "2026-06-01", "end": "2026-06-07"})

    def test_routines_save_wraps_a_single_routine_and_forwards_per_set_targets(self) -> None:
        routine = {
            "name": "Push",
            "exercises": [
                {
                    "exercise": "barbell-bench-press",
                    "sets": [{"set_type": "warmup", "kg": 40, "reps": 10}, {"kg": 60, "reps": "6-8"}],
                }
            ],
        }
        self.assert_command(
            ["routines", "save", "--routine-json", json.dumps(routine)], "save_routines", {"routines": [routine]}
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "routine.json"
            path.write_text(json.dumps(routine))
            self.assert_command(
                ["routines", "save", "--file", str(path), "--position", "0", "--days", "mon,thu"],
                "save_routines",
                {"routines": [{**routine, "position": 0, "days": ["mon", "thu"]}]},
            )

    def test_routines_save_many_routines_from_a_json_file(self) -> None:
        push = {"name": "Push", "days": ["mon"], "exercises": [{"exercise": "barbell-bench-press", "sets": 3, "reps": "8-10"}]}
        pull = {"name": "Pull", "days": ["wed"], "exercises": [{"exercise": "pull-up", "sets": 3, "reps": 8}]}
        with tempfile.TemporaryDirectory() as temp_dir:
            as_list = Path(temp_dir) / "list.json"
            as_list.write_text(json.dumps([push, pull]))
            self.assert_command(
                ["routines", "save", "--routines-file", str(as_list)], "save_routines", {"routines": [push, pull]}
            )
            wrapped = Path(temp_dir) / "wrapped.json"
            wrapped.write_text(json.dumps({"routines": [push, pull]}))
            self.assert_command(
                ["routines", "save", "--routines-file", str(wrapped)], "save_routines", {"routines": [push, pull]}
            )
        self.assert_command(
            ["routines", "save", "--routines-json", json.dumps([push])], "save_routines", {"routines": [push]}
        )
        with mock.patch("sys.stderr"):
            self.assertEqual(self.run_cli(["routines", "save", "--routines-json", "[]"])[0], 2)
            self.assertEqual(
                self.run_cli(["routines", "save", "--routines-json", json.dumps([push]), "--position", "0"])[0], 2
            )

    def test_routines_save_shortcut_expands_to_single_target_specs(self) -> None:
        self.assert_command(
            [
                "routines", "save", "--name", "Push",
                "--exercise", "barbell-bench-press:3x8-10@60",
                "--exercise", "Overhead Press:4x6@42.5",
                "--exercise", "plank:3x45s",
            ],
            "save_routines",
            {
                "routines": [
                    {
                        "name": "Push",
                        "exercises": [
                            {"exercise": "barbell-bench-press", "sets": 3, "reps": "8-10", "kg": 60.0},
                            {"exercise": "Overhead Press", "sets": 4, "reps": 6, "kg": 42.5},
                            {"exercise": "plank", "sets": 3, "seconds": 45},
                        ],
                    }
                ]
            },
        )
        for argv in (
            ["routines", "save"],
            ["routines", "save", "--name", "X", "--exercise", "bench"],
            ["routines", "save", "--routine-json", "{}", "--name", "X"],
            ["routines", "save", "--routine-json", "{}", "--routines-json", "[{}]"],
        ):
            with mock.patch("sys.stderr"):
                self.assertEqual(self.run_cli(argv)[0], 2, argv)

    def test_routines_days_sets_planned_weekdays(self) -> None:
        self.assert_command(
            ["routines", "days", "--routine", "push", "--days", "mon,thu"],
            "edit_routine",
            {"routine_id": "push", "ops": [{"op": "set_days", "days": ["mon", "thu"]}]},
        )
        self.assert_command(
            ["routines", "days", "--routine-id", "Push A", "--days", ""],
            "edit_routine",
            {"routine_id": "Push A", "ops": [{"op": "set_days", "days": []}]},
        )

    def test_routine_refs_accept_id_slug_or_name(self) -> None:
        self.assert_command(["routines", "get", "--routine", "push-a"], "get_routines",
                            {"routine_id": "push-a", "include_readiness": False})
        self.assert_command(["routines", "delete", "--routine", "Push A"], "delete_item",
                            {"type": "routine", "id": "Push A"})
        self.assert_command(["suggest-next", "--routine", "Push A"], "suggest_next", {"routine": "Push A"})
        self.assert_command(["suggest-next", "--routine-id", "push-a"], "suggest_next", {"routine": "push-a"})
        self.assert_command(["exercises", "search", "--scope", "suggested", "--routine", "push-a"],
                            "search_exercises", {"scope": "suggested", "routine_id": "push-a", "limit": 50})

    def test_memory_list_is_read_only(self) -> None:
        self.assert_command(["memory", "list"], "list_memory", {})
        with mock.patch("sys.stderr"):
            self.assertEqual(cli.main(["memory", "save"]), 2)

    def test_duplicate_of_is_passed_through_in_text_and_json(self) -> None:
        text = "duplicate of abc: an identical call was made within the last 10 minutes\nok\n"
        with mock.patch("sys.stdout", new_callable=io.StringIO) as out:
            result, _ = self.run_cli(["meals", "add", "--calories", "100"], {"exit_code": 0, "stdout": text})
        self.assertEqual(result, 0)
        self.assertIn("duplicate of abc", out.getvalue())
        body = json.dumps({"duplicate_of": "abc", "result": {"duplicate_of": "abc"}})
        with mock.patch("sys.stdout", new_callable=io.StringIO) as out:
            self.run_cli(["meals", "add", "--calories", "100", "--json"], {"exit_code": 0, "stdout": body})
        self.assertEqual(json.loads(out.getvalue())["duplicate_of"], "abc")

    def test_routine_edit_pin_move_readiness_and_delete(self) -> None:
        ops = [{"op": "set_rest", "exercise": "plank", "rest_seconds": 90}]
        self.assert_command(
            ["routines", "edit", "--routine-id", "r1", "--ops-json", json.dumps(ops), "--pin-up-next", "--position", "1"],
            "edit_routine",
            {"routine_id": "r1", "ops": ops, "pin_up_next": True, "position": 1},
        )
        self.assert_command(["routines", "pin", "--routine-id", "r1"], "edit_routine", {"routine_id": "r1", "pin_up_next": True})
        self.assert_command(["routines", "move", "--routine-id", "r1", "--position", "0"], "edit_routine",
                            {"routine_id": "r1", "position": 0})
        self.assert_command(["routines", "list", "--readiness"], "get_routines", {"include_readiness": True})
        self.assert_command(["routines", "get", "--routine-id", "r1"], "get_routines",
                            {"routine_id": "r1", "include_readiness": False})
        self.assert_command(["routines", "delete", "--routine-id", "r1"], "delete_item", {"type": "routine", "id": "r1"})

    def test_exercise_commands_map_to_v2_tools(self) -> None:
        self.assert_command(["exercises", "search", "--q", "bench", "--scope", "recent"], "search_exercises",
                            {"q": "bench", "scope": "recent", "limit": 50})
        self.assert_command(["exercises", "progress", "--exercise", "barbell-bench-press", "--range", "ALL"], "get_exercise_progress",
                            {"exercise": "barbell-bench-press", "range": "ALL"})
        self.assert_command(["exercises", "history", "--exercise", "cable-fly"], "get_exercise_progress",
                            {"exercise": "cable-fly", "range": "3M"})
        self.assert_command(
            ["exercises", "create", "--exercise-json", '{"name": "Cable Fly", "primary_muscle": "chest"}'],
            "manage_exercise",
            {"action": "create", "name": "Cable Fly", "primary_muscle": "chest"},
        )
        self.assert_command(["exercises", "rename", "--exercise", "cable-fly", "--name", "Low Cable Fly"], "manage_exercise",
                            {"action": "rename", "exercise": "cable-fly", "name": "Low Cable Fly"})
        self.assert_command(["exercises", "archive", "--exercise", "cable-fly"], "manage_exercise",
                            {"action": "archive", "exercise": "cable-fly"})
        self.assert_command(["exercises", "unarchive", "--exercise", "cable-fly"], "manage_exercise",
                            {"action": "unarchive", "exercise": "cable-fly"})
        self.assertEqual(cli.main(["exercises", "prs", "--exercise", "x"]), 2)

    def test_session_commands_map_to_v2_tools(self) -> None:
        self.assert_command(["sessions", "list", "--limit", "5"], "get_sessions", {"limit": 5})
        self.assert_command(["sessions", "get", "--session-id", "s1"], "get_sessions", {"session_id": "s1"})
        session = {"finished_at": "2026-06-12T19:00:00+00:00", "exercises": [{"exercise": "plank", "sets": [{"duration_seconds": 60}]}]}
        sent = self.assert_command(["sessions", "save", "--session-json", json.dumps(session), "--timezone", "UTC"], "log_session")
        self.assertEqual(sent, {**session, "timezone": "UTC"})
        self.assert_command(
            ["sessions", "edit", "--session-id", "s1", "--name", "Chest", "--notes", "felt good",
             "--exercises-json", '[{"exercise": "plank", "sets": []}]'],
            "edit_session",
            {"session_id": "s1", "name": "Chest", "notes": "felt good", "exercises": [{"exercise": "plank", "sets": []}]},
        )
        self.assert_command(["sessions", "sync-routine", "--session-id", "s1"], "sync_session_routine",
                            {"session_id": "s1"})
        self.assert_command(["sessions", "sync-routine", "--session-id", "s1", "--dry-run"], "sync_session_routine",
                            {"session_id": "s1", "dry_run": True})
        self.assert_command(["sessions", "sync-routine", "--session-id", "s1", "--new-routine-name", "Chest A"],
                            "sync_session_routine", {"session_id": "s1", "new_routine_name": "Chest A"})
        self.assert_command(["sessions", "delete", "--session-id", "s1"], "delete_item", {"type": "session", "id": "s1"})
        for removed in ("apply-to-routine", "save-as-routine"):
            with mock.patch("sys.stderr"):
                self.assertEqual(cli.main(["sessions", removed, "--session-id", "s1"]), 2)

    def test_recently_deleted_list_and_restore(self) -> None:
        self.assert_command(["deleted", "list"], "list_recently_deleted", {"type": "all"})
        self.assert_command(["deleted", "list", "--type", "meals"], "list_recently_deleted", {"type": "meals"})
        self.assert_command(["deleted", "restore", "--type", "session", "--id", "s1"], "restore_item",
                            {"type": "session", "id": "s1"})

    def test_profile_week_start_goals_and_dashboard_use_update_profile(self) -> None:
        self.assert_command(["profile", "week-start", "sun"], "update_profile", {"week_start": "sun"})
        self.assert_command(["profile", "update", "--profile-json", '{"injuries": ["knee"]}'], "update_profile",
                            {"profile": {"injuries": ["knee"]}})
        self.assert_command(["goals", "save", "--title", "Lift 3x", "--id", "g1"], "update_profile",
                            {"goal": {"action": "save", "title": "Lift 3x", "goal_id": "g1"}})
        self.assert_command(["goals", "archive", "--id", "g1"], "update_profile",
                            {"goal": {"action": "archive", "goal_id": "g1"}})
        self.assert_command(
            ["dashboard", "metrics", "set", "--today", "calories,protein_g", "--primary-today", "none"],
            "update_profile",
            {"dashboard": {"today_target_metrics": ["calories", "protein_g"], "primary_today_metric": None}},
        )
        with mock.patch("sys.stderr"):
            self.assertEqual(self.run_cli(["dashboard", "metrics", "set"])[0], 2)

    def test_target_and_programme_commands_use_set_targets(self) -> None:
        self.assert_command(
            ["programme", "save", "--name", "Cut", "--start", "2026-06-01", "--end", "2026-08-01", "--goal", "lose fat"],
            "set_targets",
            {"action": "save", "kind": "programme", "name": "Cut", "start": "2026-06-01", "end": "2026-08-01", "goal": "lose fat"},
        )
        self.assert_command(["programme", "activate", "--projection-id", "p1"], "set_targets",
                            {"action": "activate", "projection_id": "p1"})
        self.assert_command(["targets", "deactivate", "--projection-id", "p1"], "set_targets",
                            {"action": "deactivate", "projection_id": "p1"})
        self.assert_command(
            ["targets", "daily", "save", "--date", "2026-06-02", "--targets-json", '{"calories": 2000}'],
            "set_targets",
            {"action": "save", "kind": "daily_override", "date": "2026-06-02", "targets": {"calories": 2000}},
        )
        self.assert_command(
            ["targets", "phase", "save", "--phase-name", "Cut 1", "--start", "2026-06-01", "--end", "2026-06-30",
             "--targets-json", '{"calories": 2100}'],
            "set_targets",
            {"action": "save", "kind": "phase", "phase_name": "Cut 1", "start": "2026-06-01", "end": "2026-06-30",
             "targets": {"calories": 2100}},
        )
        self.assert_command(
            ["targets", "schedule", "save", "--start", "2026-06-01", "--end", "2026-06-30",
             "--weekday-targets-json", '{"monday": {"calories": 2000}}'],
            "set_targets",
            {"action": "save", "kind": "weekday_schedule", "start": "2026-06-01", "end": "2026-06-30",
             "weekday_targets": {"monday": {"calories": 2000}}},
        )
        for argv in (
            ["targets", "schedule", "delete", "--projection-id", "p1"],
            ["targets", "validate"],
            ["projections", "list"],
            ["recommendation", "write", "--message", "hi"],
        ):
            self.assertEqual(cli.main(argv), 2, argv)

    def test_routines_save_duplicate_name_shows_the_server_validation_error(self) -> None:
        body = json.dumps(
            {
                "detail": {
                    "message": "agent command validation failed",
                    "errors": [{"loc": ["args", "name"], "message": "a routine named 'Push' already exists"}],
                }
            }
        )
        with mock.patch.dict(
            os.environ,
            {cli.API_URL_ENV: "https://api.example.com", cli.API_KEY_ENV: "afb_agent_secret"},
            clear=False,
        ), mock.patch(
            "ai_fitness_cli.cli.request.urlopen",
            side_effect=cli.error.HTTPError("https://api.example.com", 400, "Bad Request", {}, io.BytesIO(body.encode())),
        ), mock.patch("sys.stderr", new_callable=io.StringIO) as stderr:
            result = cli.main(["routines", "save", "--name", "Push", "--exercise", "bench:3x8"])

        self.assertEqual(result, 2)
        self.assertIn("HTTP 400", stderr.getvalue())
        self.assertIn("a routine named 'Push' already exists", stderr.getvalue())

    def test_doctor_checks_the_v2_1_tool_surface(self) -> None:
        me = {"user_id": "u", "display_name": "A", "timezone": "UTC", "scope": "agent"}
        env = {cli.API_URL_ENV: "https://api.example.com", cli.API_KEY_ENV: "afb_agent_secret"}
        with mock.patch.dict(os.environ, env, clear=False), mock.patch(
            "ai_fitness_cli.cli.get_json", return_value=me
        ), mock.patch("ai_fitness_cli.cli.post_json", return_value={"exit_code": 0, "stdout": "{}"}) as post_json:
            with mock.patch("sys.stdout", new_callable=io.StringIO) as stdout:
                self.assertEqual(cli.main(["doctor"]), 0)
        self.assertIn("tool_surface=v2.1", stdout.getvalue())
        self.assertEqual(post_json.call_args.args[2]["command"], "list_memory")

        with mock.patch.dict(os.environ, env, clear=False), mock.patch(
            "ai_fitness_cli.cli.get_json", return_value=me
        ), mock.patch("ai_fitness_cli.cli.post_json", side_effect=ValueError("remote API returned HTTP 400: unknown")):
            with mock.patch("sys.stdout", new_callable=io.StringIO) as stdout:
                self.assertEqual(cli.main(["doctor"]), 1)
        self.assertIn("tool_surface=unavailable", stdout.getvalue())

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

    def test_public_remote_command_contract_is_the_v2_1_tool_set(self) -> None:
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

        # The 26-tool v2.1 registry minus the tools the CLI deliberately does not expose
        # (agents keep their own memory and can do arithmetic).
        self.assertEqual(
            collect(cli.build_parser()),
            {
                "get_context_brief", "get_day", "get_health_trends", "search_foods", "log_meal",
                "edit_meal", "get_routines", "save_routines", "edit_routine", "get_sessions",
                "log_session", "edit_session", "sync_session_routine", "search_exercises",
                "get_exercise_progress", "suggest_next", "list_memory", "manage_exercise", "delete_item",
                "list_recently_deleted", "restore_item", "set_targets", "update_profile", "log_workout",
            },
        )

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

    def test_skills_document_user_set_targets_are_never_overwritten(self) -> None:
        cli_skill = (cli.get_skill_dir("ascent-ai-cli") / "SKILL.md").read_text()
        coaching_skill = (cli.get_skill_dir("coaching-best-practices") / "SKILL.md").read_text()

        self.assertIn("skipped_user_set", cli_skill)
        self.assertIn("user_set_targets", cli_skill)
        self.assertIn("suggest the change to the user in chat", cli_skill.lower())
        self.assertIn("user_set_targets", coaching_skill)
        self.assertIn("never overwrite", coaching_skill.lower())

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
        self.assertIn("fitness foods list", cli_skill)
        self.assertIn("fitness foods lookup", cli_skill)
        self.assertIn("fitness foods search", meal_skill)
        self.assertIn("fitness foods lookup", meal_skill)
        self.assertIn("not a generic food", meal_skill)

    def test_meal_skill_leaves_portion_scaling_and_totals_to_the_server(self) -> None:
        meal_skill = (cli.get_skill_dir("meal-logging") / "SKILL.md").read_text()

        self.assertIn("The server does the meal maths", meal_skill)
        self.assertIn('"nutrition_per": 100', meal_skill)
        self.assertIn('"amount": 250', meal_skill)
        self.assertNotIn("recalculate totals, update the log", meal_skill)

    def test_program_design_skill_documents_edit_in_place_programme_updates(self) -> None:
        program_skill = (cli.get_skill_dir("fitness-program-design") / "SKILL.md").read_text()

        self.assertIn("edit the\nexisting programme, phase, or schedule in place", program_skill)
        self.assertIn("Do not create another active", program_skill)
        self.assertIn("targets deactivate --projection-id", program_skill)
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


    def test_skills_mention_only_commands_that_exist_in_v2(self) -> None:
        import re

        def resolves(words: list[str]) -> bool:
            parser = cli.build_parser()
            for word in words:
                actions = [a for a in parser._actions if isinstance(a, argparse._SubParsersAction)]
                if not actions:
                    return True  # remaining words are arguments
                choices = actions[0].choices
                if word not in choices:
                    return False
                parser = choices[word]
            return True

        removed = (
            "fitness projections", "fitness recommendation", "fitness progress", "fitness nutrition",
            "targets explain", "targets validate", "targets schedule list", "targets schedule show",
            "targets schedule update", "targets schedule delete", "meals undo", "foods get",
            "foods history", "exercises prs", "health catalog", "apply-to-routine", "save-as-routine",
            "exercises history",
        )
        checked = 0
        for name in cli.available_skill_names():
            text = (cli.get_skill_dir(name) / "SKILL.md").read_text()
            for phrase in removed:
                self.assertNotIn(phrase, text, f"{name} mentions removed command: {phrase}")
            for block in re.findall(r"```bash\n(.*?)```", text, flags=re.S):
                for line in block.splitlines():
                    match = re.match(r"fitness ((?:[a-z][a-z-]*)(?: [a-z][a-z-]*){0,3})", line.strip())
                    if not match or line.strip().startswith("fitness login"):
                        continue
                    words = match.group(1).split()
                    self.assertTrue(resolves(words), f"{name}: unknown command in: {line}")
                    checked += 1
        self.assertGreater(checked, 60)

    def test_skills_document_v2_operations(self) -> None:
        skill = (cli.get_skill_dir("ascent-ai-cli") / "SKILL.md").read_text()
        for phrase in (
            "routines save", "--routines-file", "routines days", "upsert by name", "routines edit", "routines pin", "routines move",
            "routines list --readiness", "sessions edit", "sessions sync-routine",
            "exercises progress", "suggest-next", "memory list", "duplicate_of", "sessions delete", "deleted list", "deleted restore",
            "profile week-start", "\"set_type\"", "tool_surface=v2.1",
        ):
            self.assertIn(phrase, skill)

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
