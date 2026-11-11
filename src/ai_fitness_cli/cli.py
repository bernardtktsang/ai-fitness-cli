from __future__ import annotations

import argparse
import getpass
import json
import os
import shutil
import stat
import sys
from pathlib import Path
from typing import Any
from urllib import error, request


CONFIG_ENV = "AI_FITNESS_CLI_CONFIG"
API_URL_ENV = "FITNESS_API_URL"
API_KEY_ENV = "FITNESS_API_KEY"
DEFAULT_API_URL = "https://api.ascent-ai-fitness-coach.com"
TOOL_SURFACE = "v2"
DOCTOR_PROBE_COMMAND = "get_context_brief"
LEGACY_API_URLS = {
    "https://api.bernardtktsangfitness.com": DEFAULT_API_URL,
}


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return int(exc.code) if isinstance(exc.code, int) else 2
    if not hasattr(args, "handler"):
        parser.print_help()
        return 0
    try:
        return int(args.handler(args) or 0)
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="fitness",
        description="Remote-only CLI for Ascent AI agents and users.",
    )
    subparsers = parser.add_subparsers(dest="command")

    add_login_commands(subparsers)
    add_hermes_commands(subparsers)
    add_skill_commands(subparsers)
    add_doctor_command(subparsers)
    add_context_commands(subparsers)
    add_health_commands(subparsers)
    add_workout_commands(subparsers)
    add_logbook_commands(subparsers)
    add_sync_commands(subparsers)
    add_profile_commands(subparsers)
    add_meal_commands(subparsers)
    add_food_commands(subparsers)
    add_programme_commands(subparsers)
    add_goal_commands(subparsers)
    add_target_commands(subparsers)
    add_deleted_commands(subparsers)
    add_dashboard_commands(subparsers)
    return parser


def add_common_output(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="Output format requested from the remote command.",
    )
    parser.add_argument(
        "--json",
        action="store_const",
        const="json",
        dest="format",
        help="Shortcut for --format json.",
    )



def add_timezone_override(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--timezone",
        help="IANA timezone for naive input interpretation and text display, e.g. Asia/Hong_Kong.",
    )

def add_json_input(
    parser: argparse.ArgumentParser,
    name: str,
    required: bool = True,
    file_aliases: tuple[str, ...] = (),
) -> None:
    group = parser.add_mutually_exclusive_group(required=required)
    flag = name.replace("_", "-")
    group.add_argument(f"--{flag}-json", dest=f"{name}_json", help=f"Inline JSON for {name}.")
    group.add_argument(
        f"--{flag}-file",
        *file_aliases,
        dest=f"{name}_file",
        help=f"Path to JSON file for {name}.",
    )


def add_login_commands(subparsers: argparse._SubParsersAction) -> None:
    login = subparsers.add_parser("login", help="Connect this machine to Ascent AI.")
    login.add_argument("--api-url", default=DEFAULT_API_URL, help="Backend URL without /v1.")
    login.add_argument("--api-key", help="User's afb_agent_... key. If omitted, prompts securely.")
    login.add_argument("--config-file", help="Override config file path.")
    login.add_argument("--skip-verify", action="store_true", help="Store config without calling API.")
    login.set_defaults(handler=handle_login)

    logout = subparsers.add_parser("logout", help="Remove stored remote API config.")
    logout.add_argument("--config-file", help="Override config file path.")
    logout.set_defaults(handler=handle_logout)

    config = subparsers.add_parser("config", help="Inspect local CLI config.")
    nested = config.add_subparsers(dest="config_command", required=True)
    show = nested.add_parser("show", help="Show config path and non-secret settings.")
    show.add_argument("--config-file", help="Override config file path.")
    add_common_output(show)
    show.set_defaults(handler=handle_config_show)


def add_hermes_commands(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser("hermes", help="Hermes agent integration helpers.")
    nested = parser.add_subparsers(dest="hermes_command", required=True)
    setup = nested.add_parser("setup", help="Configure Hermes to use the fitness CLI.")
    setup.add_argument("--api-url", default=os.environ.get(API_URL_ENV), help="Backend URL.")
    setup.add_argument(
        "--api-key",
        default=os.environ.get(API_KEY_ENV),
        help="User's afb_agent_... key. Can also use FITNESS_API_KEY.",
    )
    setup.add_argument("--config-file", help="Override fitness CLI config file.")
    setup.add_argument("--fitness-bin", default="fitness", help="CLI command Hermes should run.")
    setup.add_argument("--hermes-platform", default="whatsapp")
    setup.add_argument(
        "--memory-file",
        default=str(Path.home() / ".hermes" / "memories" / "USER.md"),
        help="Hermes built-in USER.md memory file.",
    )
    setup.add_argument("--skip-verify", action="store_true", help="Do not call the API first.")
    setup.add_argument("--skip-hermes-memory", action="store_true")
    setup.add_argument("--skip-enable-terminal", action="store_true")
    setup.add_argument("--restart-gateway", action="store_true")
    setup.set_defaults(handler=handle_hermes_setup)


def add_skill_commands(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser("skills", help="Read or export bundled agent skills.")
    nested = parser.add_subparsers(dest="skills_command", required=True)

    list_cmd = nested.add_parser("list", help="List bundled skills.")
    add_common_output(list_cmd)
    list_cmd.set_defaults(handler=handle_skills_list)

    show = nested.add_parser("show", help="Print a bundled skill's SKILL.md.")
    show.add_argument("skill", help="Bundled skill name.")
    show.set_defaults(handler=handle_skills_show)

    export = nested.add_parser("export", help="Copy bundled skills into an agent skill repository.")
    export.add_argument("--dest", required=True, help="Destination skill repository directory.")
    export.add_argument(
        "--skill",
        action="append",
        help="Skill name to export. Repeat to export multiple. Defaults to all.",
    )
    export.add_argument("--force", action="store_true", help="Overwrite existing skill folders.")
    export.set_defaults(handler=handle_skills_export)


def add_doctor_command(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser("doctor", help="Verify remote API login.")
    add_common_output(parser)
    parser.set_defaults(handler=handle_doctor)


# ---------------------------------------------------------------------------- v2 command tree
#
# Every remote command maps onto one tool of the backend's shared v2 agent registry (the same 22
# tools hosted chat and MCP use). `remote_command` is the tool name; `remote_build(args)` turns the
# parsed flags into that tool's input. `memory` (save_memory) and `calculate` are deliberately not
# exposed: agents keep their own memory and can do arithmetic themselves.


def compact(values: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in values.items() if value is not None}


def csv(value: str | None) -> list[str] | None:
    if value is None:
        return None
    items = [part.strip() for part in value.split(",") if part.strip()]
    return items or None


def json_value(args: argparse.Namespace, name: str) -> Any:
    """Parse `--<name>-json` / `--<name>-file`; None when neither was given."""
    inline = getattr(args, f"{name}_json", None)
    path = getattr(args, f"{name}_file", None)
    if inline is not None:
        return json.loads(inline)
    if path is not None:
        return json.loads(Path(path).read_text())
    return None


def with_timezone(payload: dict[str, Any], args: argparse.Namespace) -> dict[str, Any]:
    if getattr(args, "timezone", None) and "timezone" not in payload:
        payload = {**payload, "timezone": args.timezone}
    return payload


def set_remote(parser: argparse.ArgumentParser, tool: str, build: Any = None) -> None:
    parser.set_defaults(
        handler=handle_remote_command,
        remote_command=tool,
        remote_build=build or (lambda args: {}),
    )


def brief_builder(*include: str) -> Any:
    def build(args: argparse.Namespace) -> dict[str, Any]:
        sections = list(include) + (csv(getattr(args, "include", None)) or [])
        return compact(
            {
                "as_of": getattr(args, "as_of", None),
                "week_start": getattr(args, "week_start", None),
                "week_end": getattr(args, "week_end", None),
                "include": sections or None,
            }
        )

    return build


def add_context_commands(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser("context", help="Compact agent-ready context.")
    nested = parser.add_subparsers(dest="context_command", required=True)

    brief = nested.add_parser("brief", help="Today and week progress vs targets (start here).")
    brief.add_argument("--as-of", help="ISO date. Defaults to today in user timezone.")
    brief.add_argument("--week-start", help="ISO date.")
    brief.add_argument("--week-end", help="ISO date.")
    brief.add_argument(
        "--include",
        help="Comma-separated extras: programmes, goals, profile, dashboard, sync, metrics, memory.",
    )
    add_common_output(brief)
    set_remote(brief, "get_context_brief", brief_builder())

    day = nested.add_parser("day", help="One day in full: meals, health roll-ups, workouts, sessions.")
    day.add_argument("--date", help="ISO date. Defaults to today in user timezone.")
    add_timezone_override(day)
    add_common_output(day)
    set_remote(day, "get_day", lambda a: compact({"date": a.date, "timezone": a.timezone}))

    trend = nested.add_parser("trend", help="Rolling multi-week nutrition, workout and weight trend.")
    trend.add_argument("--as-of", help="ISO date. Defaults to today in user timezone.")
    trend.add_argument("--weeks", type=int, default=4)
    add_common_output(trend)
    set_remote(
        trend,
        "get_health_trends",
        lambda a: compact({"sections": ["trend"], "end": a.as_of, "weeks": a.weeks}),
    )


def add_health_commands(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser("health", help="Health and body trends over a date range.")
    nested = parser.add_subparsers(dest="health_command", required=True)

    def window(cmd: argparse.ArgumentParser) -> None:
        cmd.add_argument("--start", help="ISO start date.")
        cmd.add_argument("--end", help="ISO end date.")
        add_timezone_override(cmd)
        add_common_output(cmd)

    trends = nested.add_parser(
        "trends",
        help="Pick sections: health, body, nutrition, trend, workouts, samples.",
    )
    window(trends)
    trends.add_argument("--sections", help="Comma-separated sections (default health,body,nutrition,trend).")
    trends.add_argument("--weeks", type=int, help="Weeks for the trend section.")
    trends.add_argument("--body-metrics", help="Comma-separated body metrics for the body section.")
    trends.add_argument("--sample-metrics", help="Comma-separated HealthKit metrics (needed for samples).")
    set_remote(
        trends,
        "get_health_trends",
        lambda a: compact(
            {
                "start": a.start,
                "end": a.end,
                "timezone": a.timezone,
                "sections": csv(a.sections),
                "weeks": a.weeks,
                "body_metrics": csv(a.body_metrics),
                "sample_metrics": csv(a.sample_metrics),
            }
        ),
    )

    summary = nested.add_parser("summary", help="Daily Apple Health roll-ups.")
    window(summary)
    set_remote(
        summary,
        "get_health_trends",
        lambda a: compact({"sections": ["health"], "start": a.start, "end": a.end, "timezone": a.timezone}),
    )

    body = nested.add_parser("body", help="Body composition measurements.")
    window(body)
    body.add_argument("--metrics", help="Comma-separated body metric names.")
    set_remote(
        body,
        "get_health_trends",
        lambda a: compact(
            {
                "sections": ["body"],
                "start": a.start,
                "end": a.end,
                "timezone": a.timezone,
                "body_metrics": csv(a.metrics),
            }
        ),
    )


def add_workout_commands(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser("workouts", help="Non-strength workouts (runs, rides, ...).")
    nested = parser.add_subparsers(dest="workout_command", required=True)

    list_cmd = nested.add_parser("list", help="List workouts in a date range.")
    list_cmd.add_argument("--start", required=True, help="ISO start date.")
    list_cmd.add_argument("--end", required=True, help="ISO end date.")
    add_timezone_override(list_cmd)
    add_common_output(list_cmd)
    set_remote(
        list_cmd,
        "get_health_trends",
        lambda a: compact({"sections": ["workouts"], "start": a.start, "end": a.end, "timezone": a.timezone}),
    )

    save = nested.add_parser(
        "save",
        help="Log a workout from JSON: workout_type, start_time, end_time (+ optional energy, notes).",
    )
    add_json_input(save, "workout", file_aliases=("--file",))
    add_timezone_override(save)
    add_common_output(save)
    set_remote(
        save, "log_workout", lambda a: {"workout": with_timezone(json_value(a, "workout"), a)}
    )

    update = nested.add_parser("update", help="Correct a logged workout from JSON changes.")
    update.add_argument("--workout-id", required=True)
    add_json_input(update, "changes", file_aliases=("--file",))
    add_timezone_override(update)
    add_common_output(update)
    set_remote(
        update,
        "log_workout",
        lambda a: {"workout_id": a.workout_id, "changes": with_timezone(json_value(a, "changes"), a)},
    )

    delete = nested.add_parser("delete", help="Delete a workout (restorable for 30 days).")
    delete.add_argument("--workout-id", required=True)
    add_common_output(delete)
    set_remote(delete, "delete_item", lambda a: {"type": "workout", "id": a.workout_id})


def add_sync_commands(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser("sync", help="Sync status.")
    nested = parser.add_subparsers(dest="sync_command", required=True)
    status = nested.add_parser("status", help="Show health data sync freshness.")
    add_common_output(status)
    set_remote(status, "get_context_brief", brief_builder("sync"))


def add_profile_commands(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser("profile", help="User profile reads/writes.")
    nested = parser.add_subparsers(dest="profile_command", required=True)
    show = nested.add_parser("show", help="Show user profile.")
    add_common_output(show)
    set_remote(show, "get_context_brief", brief_builder("profile"))

    update = nested.add_parser("update", help="Merge profile JSON (injuries, preferences, ...).")
    add_json_input(update, "profile")
    add_common_output(update)
    set_remote(update, "update_profile", lambda a: {"profile": json_value(a, "profile")})

    week_start = nested.add_parser("week-start", help="Set the first day of the user's week.")
    week_start.add_argument("day", choices=("mon", "sun", "sat"))
    add_common_output(week_start)
    set_remote(week_start, "update_profile", lambda a: {"week_start": a.day})


def add_meal_commands(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser("meals", help="Nutrition meal reads/writes.")
    nested = parser.add_subparsers(dest="meal_command", required=True)

    summary = nested.add_parser("summary", help="Daily nutrition totals.")
    summary.add_argument("--start", help="ISO start date.")
    summary.add_argument("--end", help="ISO end date.")
    add_timezone_override(summary)
    add_common_output(summary)
    set_remote(
        summary,
        "get_health_trends",
        lambda a: compact({"sections": ["nutrition"], "start": a.start, "end": a.end, "timezone": a.timezone}),
    )

    list_cmd = nested.add_parser("list", help="List one day's meals (with totals).")
    list_cmd.add_argument("--date", help="ISO date. Defaults to today in user timezone.")
    add_timezone_override(list_cmd)
    add_common_output(list_cmd)
    set_remote(list_cmd, "get_day", lambda a: compact({"date": a.date, "timezone": a.timezone}))

    save = nested.add_parser(
        "save",
        help=(
            "Log a meal from JSON. Omit eaten_at for just-now meals; "
            "use eaten_at plus timezone for specified local meal times."
        ),
    )
    add_json_input(save, "meal", file_aliases=("--file",))
    add_timezone_override(save)
    add_common_output(save)
    set_remote(save, "log_meal", lambda a: {"meal": with_timezone(json_value(a, "meal"), a)})

    update = nested.add_parser("update", help="Correct a logged meal from JSON field changes.")
    update.add_argument("--meal-id", required=True)
    add_json_input(update, "meal_update", file_aliases=("--file",))
    add_timezone_override(update)
    add_common_output(update)
    set_remote(
        update,
        "edit_meal",
        lambda a: {"meal_id": a.meal_id, "updates": with_timezone(json_value(a, "meal_update"), a)},
    )

    delete = nested.add_parser("delete", help="Delete a meal (restorable for 30 days).")
    delete.add_argument("--meal-id", required=True)
    add_common_output(delete)
    set_remote(delete, "delete_item", lambda a: {"type": "meal", "id": a.meal_id})

    add = nested.add_parser("add", help="Quick add one meal from flat macros (saved as a single item).")
    add.add_argument("--title", help="Short meal name, e.g. 'Protein shake' (max 80 chars).")
    add.add_argument("--calories", type=float, required=True)
    add.add_argument("--protein", type=float, default=0, help="Protein grams.")
    add.add_argument("--carbs", type=float, default=0, help="Carb grams.")
    add.add_argument("--fat", type=float, default=0, help="Fat grams.")
    add.add_argument("--eaten-at", help="Bare local datetime; omit for just-now meals.")
    add_timezone_override(add)
    add_common_output(add)
    set_remote(add, "log_meal", build_quick_add_meal)

    scale = nested.add_parser("scale", help="Scale every item in a meal (e.g. 1.5 servings).")
    scale.add_argument("--meal-id", required=True)
    scale.add_argument("--servings-scale", type=float, required=True, help="Multiplier, 0.1-20.")
    add_common_output(scale)
    set_remote(
        scale,
        "edit_meal",
        lambda a: {"meal_id": a.meal_id, "servings_scale": a.servings_scale},
    )

    item_update = nested.add_parser(
        "item-update", help="Scale or override one meal item (servings_scale and/or field overrides)."
    )
    item_update.add_argument("--meal-id", required=True)
    item_update.add_argument("--item-id", required=True)
    add_json_input(item_update, "item_changes", file_aliases=("--file",))
    add_common_output(item_update)
    set_remote(
        item_update,
        "edit_meal",
        lambda a: {
            "meal_id": a.meal_id,
            "item_id": a.item_id,
            "item_changes": json_value(a, "item_changes"),
        },
    )

    item_delete = nested.add_parser("item-delete", help="Remove one item from a meal.")
    item_delete.add_argument("--meal-id", required=True)
    item_delete.add_argument("--item-id", required=True)
    add_common_output(item_delete)
    set_remote(
        item_delete,
        "edit_meal",
        lambda a: {"meal_id": a.meal_id, "item_id": a.item_id, "remove_item": True},
    )


def build_quick_add_meal(args: argparse.Namespace) -> dict[str, Any]:
    meal: dict[str, Any] = {
        "items": [
            {
                "name": args.title or "Quick add",
                "calories": args.calories,
                "protein_g": args.protein,
                "carbs_g": args.carbs,
                "fat_g": args.fat,
            }
        ],
        "source": "hermes",
        "estimate_source": "user_entered",
    }
    if args.title:
        meal["title"] = args.title
    if args.eaten_at:
        meal["eaten_at"] = args.eaten_at
    return {"meal": with_timezone(meal, args)}


def add_food_filters(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--start", help="ISO start date.")
    parser.add_argument("--end", help="ISO end date.")
    parser.add_argument("--meal-type", choices=("breakfast", "lunch", "dinner", "snack"))


def add_food_commands(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser("foods", help="Food history and nutrition lookups.")
    nested = parser.add_subparsers(dest="food_command", required=True)

    def filters(a: argparse.Namespace) -> dict[str, Any]:
        return {
            "start": a.start,
            "end": a.end,
            "meal_type": a.meal_type,
            "timezone": a.timezone,
            "limit": a.limit,
        }

    search = nested.add_parser("search", help="Search foods the user has logged before.")
    search.add_argument("query")
    search.add_argument("--limit", type=int, default=10)
    add_food_filters(search)
    add_timezone_override(search)
    add_common_output(search)
    set_remote(
        search, "search_foods", lambda a: compact({"mode": "history", "query": a.query, **filters(a)})
    )

    list_cmd = nested.add_parser("list", help="The user's most frequently logged foods.")
    list_cmd.add_argument("--limit", type=int, default=20)
    add_food_filters(list_cmd)
    add_timezone_override(list_cmd)
    add_common_output(list_cmd)
    set_remote(list_cmd, "search_foods", lambda a: compact({"mode": "frequent", **filters(a)}))

    lookup = nested.add_parser(
        "lookup", help="Look up structured macros for an unfamiliar or branded food."
    )
    lookup.add_argument("query")
    lookup.add_argument("--portion-hint")
    add_common_output(lookup)
    set_remote(
        lookup,
        "search_foods",
        lambda a: compact({"mode": "lookup", "query": a.query, "portion_hint": a.portion_hint}),
    )


def add_goal_commands(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser(
        "goals", help="The user's goals: short text records (no numbers; targets hold numbers)."
    )
    nested = parser.add_subparsers(dest="goals_command", required=True)

    list_cmd = nested.add_parser("list", help="List goals, newest first.")
    add_common_output(list_cmd)
    set_remote(list_cmd, "get_context_brief", brief_builder("goals"))

    save = nested.add_parser("save", help="Create a goal, or update one with --id.")
    save.add_argument("--title", required=True, help="Up to 120 characters.")
    save.add_argument("--description", help="Up to 2000 characters.")
    save.add_argument("--id", help="Goal id to update instead of creating a new goal.")
    add_common_output(save)
    set_remote(
        save,
        "update_profile",
        lambda a: {
            "goal": compact(
                {"action": "save", "title": a.title, "description": a.description, "goal_id": a.id}
            )
        },
    )

    archive = nested.add_parser("archive", help="Archive a goal (the user can restore it in the app).")
    archive.add_argument("--id", required=True)
    add_common_output(archive)
    set_remote(archive, "update_profile", lambda a: {"goal": {"action": "archive", "goal_id": a.id}})


def add_programme_commands(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser("programme", help="Programme reads and writes.")
    nested = parser.add_subparsers(dest="programme_command", required=True)

    list_cmd = nested.add_parser("list", help="List saved programmes and active status.")
    add_common_output(list_cmd)
    set_remote(list_cmd, "get_context_brief", brief_builder("programmes"))

    save = nested.add_parser("save", help="Save a programme (updates in place when name and dates match).")
    save.add_argument("--name", required=True)
    save.add_argument("--start", required=True, help="ISO start date.")
    save.add_argument("--end", required=True, help="ISO end date.")
    save.add_argument("--goal", required=True)
    add_json_input(save, "payload", required=False)
    add_common_output(save)
    set_remote(
        save,
        "set_targets",
        lambda a: compact(
            {
                "action": "save",
                "kind": "programme",
                "name": a.name,
                "start": a.start,
                "end": a.end,
                "goal": a.goal,
                "payload": json_value(a, "payload"),
            }
        ),
    )

    activate = nested.add_parser("activate", help="Activate one saved programme.")
    activate.add_argument("--projection-id", required=True)
    add_common_output(activate)
    set_remote(
        activate,
        "set_targets",
        lambda a: {"action": "activate", "projection_id": a.projection_id},
    )


def add_target_commands(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser("targets", help="Target planning reads/writes.")
    nested = parser.add_subparsers(dest="target_command", required=True)

    show = nested.add_parser("show", help="Effective targets and where they come from for a date.")
    show.add_argument("--as-of", help="ISO date. Defaults to today in user timezone.")
    add_common_output(show)
    set_remote(show, "get_context_brief", brief_builder())

    phase = nested.add_parser("phase", help="Phase target commands.")
    phase_nested = phase.add_subparsers(dest="target_phase_command", required=True)
    phase_save = phase_nested.add_parser("save", help="Save a phase's daily targets.")
    phase_save.add_argument("--phase-name", required=True)
    phase_save.add_argument("--start", required=True, help="ISO start date.")
    phase_save.add_argument("--end", required=True, help="ISO end date.")
    phase_save.add_argument("--status")
    phase_save.add_argument("--programme-id")
    phase_save.add_argument("--rationale")
    add_json_input(phase_save, "targets")
    add_json_input(phase_save, "weekly_overrides", required=False)
    add_json_input(phase_save, "payload", required=False)
    add_common_output(phase_save)
    set_remote(
        phase_save,
        "set_targets",
        lambda a: compact(
            {
                "action": "save",
                "kind": "phase",
                "phase_name": a.phase_name,
                "start": a.start,
                "end": a.end,
                "status": a.status,
                "programme_id": a.programme_id,
                "rationale": a.rationale,
                "targets": json_value(a, "targets"),
                "weekly_overrides": json_value(a, "weekly_overrides"),
                "payload": json_value(a, "payload"),
            }
        ),
    )

    schedule = nested.add_parser("schedule", help="Recurring weekday target schedules.")
    schedule_nested = schedule.add_subparsers(dest="target_schedule_command", required=True)
    schedule_save = schedule_nested.add_parser(
        "save", help="Save a repeating weekday schedule (--projection-id updates an existing one)."
    )
    schedule_save.add_argument("--projection-id", help="Existing schedule to update.")
    schedule_save.add_argument("--start", help="ISO start date (required unless updating).")
    schedule_save.add_argument("--end", help="ISO end date (required unless updating).")
    schedule_save.add_argument("--status")
    schedule_save.add_argument("--name")
    schedule_save.add_argument("--phase-name")
    schedule_save.add_argument("--programme-id")
    schedule_save.add_argument("--rationale")
    add_json_input(schedule_save, "default_targets", required=False)
    add_json_input(schedule_save, "weekday_targets", required=False)
    add_json_input(schedule_save, "date_overrides", required=False)
    add_json_input(schedule_save, "payload", required=False)
    add_common_output(schedule_save)
    set_remote(
        schedule_save,
        "set_targets",
        lambda a: compact(
            {
                "action": "save",
                "kind": "weekday_schedule",
                "projection_id": a.projection_id,
                "start": a.start,
                "end": a.end,
                "status": a.status,
                "name": a.name,
                "phase_name": a.phase_name,
                "programme_id": a.programme_id,
                "rationale": a.rationale,
                "default_targets": json_value(a, "default_targets"),
                "weekday_targets": json_value(a, "weekday_targets"),
                "date_overrides": json_value(a, "date_overrides"),
                "payload": json_value(a, "payload"),
            }
        ),
    )

    deactivate = nested.add_parser(
        "deactivate", help="Retire a phase, schedule or programme (reversible)."
    )
    deactivate.add_argument("--projection-id", required=True)
    add_common_output(deactivate)
    set_remote(
        deactivate,
        "set_targets",
        lambda a: {"action": "deactivate", "projection_id": a.projection_id},
    )

    daily = nested.add_parser("daily", help="Daily target override commands.")
    daily_nested = daily.add_subparsers(dest="target_daily_command", required=True)
    daily_save = daily_nested.add_parser("save", help="Save one date-specific target override.")
    daily_save.add_argument("--date", required=True, help="ISO target date.")
    daily_save.add_argument("--status")
    daily_save.add_argument("--rationale")
    add_json_input(daily_save, "targets")
    add_json_input(daily_save, "payload", required=False)
    add_common_output(daily_save)
    set_remote(
        daily_save,
        "set_targets",
        lambda a: compact(
            {
                "action": "save",
                "kind": "daily_override",
                "date": a.date,
                "status": a.status,
                "rationale": a.rationale,
                "targets": json_value(a, "targets"),
                "payload": json_value(a, "payload"),
            }
        ),
    )


def add_dashboard_commands(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser("dashboard", help="Dashboard preferences.")
    nested = parser.add_subparsers(dest="dashboard_command", required=True)
    metrics = nested.add_parser("metrics", help="Which target metrics the Today and Week views show.")
    metrics_nested = metrics.add_subparsers(dest="dashboard_metrics_command", required=True)

    show = metrics_nested.add_parser("show", help="Show dashboard metric preferences and valid keys.")
    add_common_output(show)
    set_remote(show, "get_context_brief", brief_builder("dashboard"))

    set_cmd = metrics_nested.add_parser("set", help="Set synced Today/Week target metrics.")
    set_cmd.add_argument("--today", help="Comma-separated metric keys.")
    set_cmd.add_argument("--week", help="Comma-separated metric keys.")
    set_cmd.add_argument(
        "--primary-today",
        help="Metric key for the Today hero card; must be in --today. Pass 'none' to clear.",
    )
    add_common_output(set_cmd)
    set_remote(set_cmd, "update_profile", build_dashboard_prefs)


def build_dashboard_prefs(args: argparse.Namespace) -> dict[str, Any]:
    prefs: dict[str, Any] = {}
    if args.today is not None:
        prefs["today_target_metrics"] = csv(args.today) or []
    if args.week is not None:
        prefs["week_target_metrics"] = csv(args.week) or []
    if args.primary_today is not None:
        prefs["primary_today_metric"] = (
            None if args.primary_today.lower() == "none" else args.primary_today
        )
    if not prefs:
        raise ValueError("provide at least one of --today, --week, --primary-today")
    return {"dashboard": prefs}


EXERCISE_SPEC_HELP = (
    "Single-target shortcut '<exercise>:<sets>x<reps>[@<kg>]', e.g. "
    "'barbell-bench-press:3x8-10@60' or timed 'plank:3x45s'. Repeat in workout order. "
    "Use --routine-json for per-set targets (warm-ups, drop sets, rest)."
)


def parse_exercise_spec(spec: str) -> dict[str, Any]:
    name, sep, rest = spec.rpartition(":")
    if not sep or not name.strip():
        raise ValueError(f"bad --exercise '{spec}'; expected <exercise>:<sets>x<reps>[@<kg>]")
    count_text, x, target = rest.partition("x")
    if not x or not count_text.strip().isdigit():
        raise ValueError(f"bad --exercise '{spec}'; expected <exercise>:<sets>x<reps>[@<kg>]")
    entry: dict[str, Any] = {"exercise": name.strip(), "sets": int(count_text)}
    target, _, kg = target.partition("@")
    target = target.strip()
    if target.endswith("s") and target[:-1].isdigit():
        entry["seconds"] = int(target[:-1])
    elif target.isdigit():
        entry["reps"] = int(target)
    elif target:
        entry["reps"] = target
    if kg.strip():
        entry["kg"] = float(kg)
    return entry


def build_routine_save(args: argparse.Namespace) -> dict[str, Any]:
    body = json_value(args, "routine")
    if body is None:
        if not args.name:
            raise ValueError("provide --routine-json/--file, or --name with --exercise")
        body = {"name": args.name, "exercises": [parse_exercise_spec(s) for s in args.exercise or []]}
    elif args.name or args.exercise:
        raise ValueError("use either --routine-json/--file or --name/--exercise, not both")
    if args.position is not None:
        body = {**body, "position": args.position}
    return body


def add_logbook_commands(subparsers: argparse._SubParsersAction) -> None:
    """Strength logbook: routines, exercise library, sessions, history and PRs (kg)."""
    routines = subparsers.add_parser("routines", help="Workout routines (e.g. a Push/Pull/Legs split).")
    nested = routines.add_subparsers(dest="routine_command", required=True)

    list_cmd = nested.add_parser("list", help="List routines in order with per-set targets.")
    list_cmd.add_argument("--readiness", action="store_true", help="Add muscle readiness and the up-next pick.")
    add_common_output(list_cmd)
    set_remote(list_cmd, "get_routines", lambda a: {"include_readiness": a.readiness})

    get = nested.add_parser("get", help="Show one routine in full.")
    get.add_argument("--routine-id", required=True)
    get.add_argument("--readiness", action="store_true", help="Add muscle readiness and the up-next pick.")
    add_common_output(get)
    set_remote(
        get, "get_routines", lambda a: {"routine_id": a.routine_id, "include_readiness": a.readiness}
    )

    save = nested.add_parser(
        "save",
        help=(
            "Create a routine, or replace the one with the same name (upsert by name, "
            "case-insensitive). Give per-set targets as JSON: "
            '{"name": "Push", "exercises": [{"exercise": "<slug or name>", "sets": '
            '[{"set_type": "warmup", "kg": 40, "reps": 10}, {"kg": 60, "reps": "6-8"}]}]}; '
            "or use --name with --exercise shortcuts."
        ),
    )
    add_json_input(save, "routine", required=False, file_aliases=("--file",))
    save.add_argument("--name", help="Routine name (with --exercise).")
    save.add_argument("--exercise", action="append", help=EXERCISE_SPEC_HELP)
    save.add_argument("--position", type=int, help="Place the routine at this index in the routine order.")
    add_common_output(save)
    set_remote(save, "save_routine", build_routine_save)

    edit = nested.add_parser(
        "edit",
        help=(
            "Edit part of a routine atomically with ops JSON: rename, add_exercise, remove_exercise, "
            "move_exercise, replace_sets, set_rest; optionally pin or move it."
        ),
    )
    edit.add_argument("--routine-id", required=True)
    add_json_input(edit, "ops", required=False, file_aliases=("--file",))
    edit.add_argument("--pin-up-next", action="store_true", help="Pin as today's up-next routine.")
    edit.add_argument("--position", type=int, help="Move to this index in the routine order.")
    add_common_output(edit)
    set_remote(
        edit,
        "edit_routine",
        lambda a: compact(
            {
                "routine_id": a.routine_id,
                "ops": json_value(a, "ops"),
                "pin_up_next": True if a.pin_up_next else None,
                "position": a.position,
            }
        ),
    )

    pin = nested.add_parser("pin", help="Pin a routine as today's up-next pick.")
    pin.add_argument("--routine-id", required=True)
    add_common_output(pin)
    set_remote(pin, "edit_routine", lambda a: {"routine_id": a.routine_id, "pin_up_next": True})

    move = nested.add_parser("move", help="Move a routine to a position in the routine order.")
    move.add_argument("--routine-id", required=True)
    move.add_argument("--position", type=int, required=True, help="0-based index.")
    add_common_output(move)
    set_remote(move, "edit_routine", lambda a: {"routine_id": a.routine_id, "position": a.position})

    delete = nested.add_parser("delete", help="Delete a routine (restorable for 30 days).")
    delete.add_argument("--routine-id", required=True)
    add_common_output(delete)
    set_remote(delete, "delete_item", lambda a: {"type": "routine", "id": a.routine_id})

    exercises = subparsers.add_parser("exercises", help="Exercise library, history and personal records.")
    nested = exercises.add_subparsers(dest="exercise_command", required=True)
    search = nested.add_parser("search", help="Search the exercise library.")
    search.add_argument("--q", help="Name search.")
    search.add_argument("--muscle", help="chest, back, shoulders, biceps, triceps, forearms, quads, hamstrings, glutes, calves, core, full_body.")
    search.add_argument("--equipment", help="barbell, dumbbell, machine, cable, bodyweight, kettlebell, band, smith_machine, other.")
    search.add_argument("--scope", choices=("all", "recent", "suggested"), default="all")
    search.add_argument("--routine-id", help="Routine to suggest exercises for (with --scope suggested).")
    search.add_argument("--limit", type=int, default=50)
    add_common_output(search)
    set_remote(
        search,
        "search_exercises",
        lambda a: compact(
            {
                "q": a.q,
                "muscle": a.muscle,
                "equipment": a.equipment,
                "scope": a.scope,
                "routine_id": a.routine_id,
                "limit": a.limit,
            }
        ),
    )

    history = nested.add_parser("history", help="Progress series and personal records for one exercise.")
    history.add_argument("--exercise", required=True, help="Slug, exact name or id.")
    history.add_argument("--metric", help="weighted: heaviest|e1rm|volume; bodyweight: reps|added_kg; assisted: assistance; timed: hold.")
    history.add_argument("--range", choices=("1M", "3M", "1Y", "ALL"), default="3M")
    add_common_output(history)
    set_remote(
        history,
        "search_exercises",
        lambda a: compact({"exercise": a.exercise, "metric": a.metric, "range": a.range}),
    )

    create = nested.add_parser(
        "create",
        help=(
            "Create a custom exercise from JSON: name, exercise_type "
            "(weighted|bodyweight|assisted|timed), primary_muscle, equipment, secondary_muscles."
        ),
    )
    add_json_input(create, "exercise", file_aliases=("--file",))
    add_common_output(create)
    set_remote(create, "manage_exercise", lambda a: {"action": "create", **json_value(a, "exercise")})

    rename = nested.add_parser("rename", help="Rename one of the user's custom exercises.")
    rename.add_argument("--exercise", required=True, help="Slug, exact name or id.")
    rename.add_argument("--name", required=True)
    add_common_output(rename)
    set_remote(
        rename,
        "manage_exercise",
        lambda a: {"action": "rename", "exercise": a.exercise, "name": a.name},
    )
    for action, text in (("archive", "Archive"), ("unarchive", "Unarchive")):
        cmd = nested.add_parser(action, help=f"{text} one of the user's custom exercises.")
        cmd.add_argument("--exercise", required=True, help="Slug, exact name or id.")
        add_common_output(cmd)
        set_remote(cmd, "manage_exercise", lambda a, action=action: {"action": action, "exercise": a.exercise})

    sessions = subparsers.add_parser("sessions", help="Finished strength sessions (sets, PRs).")
    nested = sessions.add_subparsers(dest="session_command", required=True)
    list_sessions = nested.add_parser("list", help="List finished sessions with sets and PRs.")
    list_sessions.add_argument("--start", help="ISO start date.")
    list_sessions.add_argument("--end", help="ISO end date.")
    list_sessions.add_argument("--limit", type=int, default=20)
    add_common_output(list_sessions)
    set_remote(
        list_sessions,
        "get_sessions",
        lambda a: compact({"start": a.start, "end": a.end, "limit": a.limit}),
    )

    get_session = nested.add_parser("get", help="Show one finished session.")
    get_session.add_argument("--session-id", required=True)
    add_common_output(get_session)
    set_remote(get_session, "get_sessions", lambda a: {"session_id": a.session_id})

    save_session = nested.add_parser(
        "save",
        help=(
            "Backfill a finished session from JSON (finished_at required). Shape: "
            '{"name": "Push", "started_at": "...", "finished_at": "...", "exercises": '
            '[{"exercise": "<slug or name>", "sets": [{"kg": 80, "reps": 8}, '
            '{"kg": 40, "reps": 10, "set_type": "warmup"}]}]}. '
            "Live sessions are started and finished in the app."
        ),
    )
    add_json_input(save_session, "session", file_aliases=("--file",))
    add_timezone_override(save_session)
    add_common_output(save_session)
    set_remote(
        save_session, "log_session", lambda a: with_timezone(json_value(a, "session"), a)
    )

    edit_session = nested.add_parser(
        "edit", help="Edit a finished session: name, notes, start time or replace its exercises."
    )
    edit_session.add_argument("--session-id", required=True)
    edit_session.add_argument("--name")
    edit_session.add_argument("--notes")
    edit_session.add_argument("--started-at", help="Local datetime (with --timezone) or with offset.")
    add_json_input(edit_session, "exercises", required=False)
    add_timezone_override(edit_session)
    add_common_output(edit_session)
    set_remote(
        edit_session,
        "edit_session",
        lambda a: compact(
            {
                "session_id": a.session_id,
                "name": a.name,
                "notes": a.notes,
                "started_at": a.started_at,
                "exercises": json_value(a, "exercises"),
                "timezone": a.timezone,
            }
        ),
    )

    apply_cmd = nested.add_parser(
        "apply-to-routine",
        help="Write a session's exercises and sets back to its source routine (preview first).",
    )
    apply_cmd.add_argument("--session-id", required=True)
    mode = apply_cmd.add_mutually_exclusive_group(required=True)
    mode.add_argument("--preview", action="store_true", help="Show the diff without changing the routine.")
    mode.add_argument("--apply", action="store_true", help="Apply the diff to the routine.")
    add_common_output(apply_cmd)
    set_remote(
        apply_cmd,
        "edit_session",
        lambda a: {"session_id": a.session_id, "routine_sync": "apply" if a.apply else "preview"},
    )

    save_routine = nested.add_parser("save-as-routine", help="Save a session's structure as a new routine.")
    save_routine.add_argument("--session-id", required=True)
    save_routine.add_argument("--routine-name", help="Defaults to the session's name.")
    add_common_output(save_routine)
    set_remote(
        save_routine,
        "edit_session",
        lambda a: compact(
            {
                "session_id": a.session_id,
                "routine_sync": "save_as_routine",
                "routine_name": a.routine_name,
            }
        ),
    )

    delete_session = nested.add_parser("delete", help="Delete a session (restorable for 30 days).")
    delete_session.add_argument("--session-id", required=True)
    add_common_output(delete_session)
    set_remote(delete_session, "delete_item", lambda a: {"type": "session", "id": a.session_id})


def add_deleted_commands(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser(
        "deleted", help="Recently deleted meals, sessions, routines and workouts (kept 30 days)."
    )
    nested = parser.add_subparsers(dest="deleted_command", required=True)
    list_cmd = nested.add_parser("list", help="List restorable items with who deleted them.")
    list_cmd.add_argument("--type", choices=("all", "workouts", "meals", "routines"), default="all")
    add_common_output(list_cmd)
    set_remote(list_cmd, "list_recently_deleted", lambda a: {"type": a.type})

    restore = nested.add_parser("restore", help="Restore an item from Recently deleted.")
    restore.add_argument("--type", required=True, choices=("meal", "session", "routine", "workout"))
    restore.add_argument("--id", required=True)
    add_common_output(restore)
    set_remote(restore, "restore_item", lambda a: {"type": a.type, "id": a.id})


def handle_login(args: argparse.Namespace) -> int:
    api_url = normalize_api_url(args.api_url)
    api_key = (args.api_key or prompt_for_agent_key()).strip()
    if not api_key.startswith("afb_agent_"):
        raise ValueError("login requires an afb_agent_... key")
    response = {} if args.skip_verify else get_json(f"{api_url}/v1/agent/me", api_key)
    config_path = get_config_path(args.config_file)
    write_config(config_path, {"api_url": api_url, "api_key": api_key})
    if response:
        print(f"Connected as {response.get('display_name') or response.get('user_id')}")
    print(f"Saved Agent key: {display_key_prefix(api_key)}")
    print(f"API URL: {api_url}")
    print(f"Config: {config_path}")
    print("Run `fitness doctor` to verify your setup.")
    return 0


def handle_logout(args: argparse.Namespace) -> int:
    config_path = get_config_path(args.config_file)
    if config_path.exists():
        config_path.unlink()
        print(f"removed config: {config_path}")
    else:
        print(f"config already absent: {config_path}")
    return 0


def handle_config_show(args: argparse.Namespace) -> int:
    config_path = get_config_path(args.config_file)
    config = read_config(config_path)
    env_url = os.environ.get(API_URL_ENV)
    env_key = os.environ.get(API_KEY_ENV)
    result = {
        "config_path": str(config_path),
        "config_exists": config_path.exists(),
        "api_url": env_url or config.get("api_url"),
        "api_key_source": "env" if env_key else "config" if config.get("api_key") else None,
    }
    if args.format == "json":
        print(json.dumps(result, indent=2))
    else:
        print(f"config_path={result['config_path']}")
        print(f"config_exists={str(result['config_exists']).lower()}")
        print(f"api_url={result['api_url'] or ''}")
        print(f"api_key_source={result['api_key_source'] or ''}")
    return 0


def handle_hermes_setup(args: argparse.Namespace) -> int:
    from ai_fitness_cli.hermes_setup import configure

    return configure(args)


def handle_skills_list(args: argparse.Namespace) -> int:
    skills = bundled_skills()
    if args.format == "json":
        print(json.dumps({"skills": skills}, indent=2))
    else:
        for skill in skills:
            print(f"{skill['name']}: {skill['description']}")
    return 0


def handle_skills_show(args: argparse.Namespace) -> int:
    skill_dir = get_skill_dir(args.skill)
    print((skill_dir / "SKILL.md").read_text(), end="")
    return 0


def handle_skills_export(args: argparse.Namespace) -> int:
    selected = args.skill or available_skill_names()
    dest_dir = Path(args.dest).expanduser()
    dest_dir.mkdir(parents=True, exist_ok=True)

    installed: list[str] = []
    skipped: list[str] = []
    for skill_name in selected:
        source = get_skill_dir(skill_name)
        target = dest_dir / skill_name
        if target.exists():
            if not args.force:
                skipped.append(skill_name)
                continue
            shutil.rmtree(target)
        shutil.copytree(source, target)
        installed.append(skill_name)

    for skill_name in installed:
        print(f"exported {skill_name} -> {dest_dir / skill_name}")
    for skill_name in skipped:
        print(f"skipped {skill_name}; already exists (use --force to overwrite)")
    return 0


def handle_doctor(args: argparse.Namespace) -> int:
    api_url, api_key, source = get_credentials()
    response = get_json(f"{api_url}/v1/agent/me", api_key)
    result = {"mode": "remote", "api_url": api_url, "credential_source": source, **response}
    # Read-only probe of the v2 command surface (a server still on the old dotted commands
    # rejects the tool name).
    try:
        post_json(
            f"{api_url}/v1/agent/commands",
            api_key,
            {"command": DOCTOR_PROBE_COMMAND, "args": {"format": "json"}},
        )
        result["tool_surface"] = TOOL_SURFACE
        exit_code = 0
    except ValueError as exc:
        result["tool_surface"] = f"unavailable: {exc}"
        exit_code = 1
    if args.format == "json":
        print(json.dumps(result, indent=2))
    else:
        print("mode=remote")
        print(f"api_url={api_url}")
        print(f"credential_source={source}")
        print(f"user_id={response.get('user_id')}")
        print(f"display_name={response.get('display_name')}")
        print(f"timezone={response.get('timezone')}")
        print(f"scope={response.get('scope')}")
        print(f"tool_surface={result['tool_surface']}")
    return exit_code


def handle_remote_command(args: argparse.Namespace) -> int:
    api_url, api_key, _ = get_credentials()
    payload = {
        "command": args.remote_command,
        "args": {**args.remote_build(args), "format": args.format},
    }
    response = post_json(f"{api_url}/v1/agent/commands", api_key, payload)
    stdout = response.get("stdout") or ""
    if stdout:
        print(stdout, end="" if stdout.endswith("\n") else "\n")
    return int(response.get("exit_code") or 0)


def prompt_for_agent_key() -> str:
    print(
        "Open Ascent AI on your iPhone:\n"
        "Settings -> AI Agent -> Generate Agent Key\n\n"
        "Paste the Agent API key here. It starts with afb_agent_.\n"
        "The key stays on this machine and is never printed back."
    )
    return getpass.getpass("Agent API key: ")


def display_key_prefix(api_key: str) -> str:
    visible_chars = 16 if len(api_key) > 16 else 8
    return f"{api_key[:visible_chars]}..."


def get_credentials() -> tuple[str, str, str]:
    env_url = os.environ.get(API_URL_ENV)
    env_key = os.environ.get(API_KEY_ENV)
    if env_url and env_key:
        return normalize_api_url(env_url), env_key, "env"
    config_path = get_config_path(None)
    config = read_config(config_path)
    api_url = config.get("api_url")
    api_key = config.get("api_key")
    if not api_url or not api_key:
        raise ValueError("not logged in; run `fitness login`")
    return normalize_api_url(api_url), api_key, str(config_path)


def get_config_path(override: str | None) -> Path:
    if override:
        return Path(override).expanduser()
    if env_path := os.environ.get(CONFIG_ENV):
        return Path(env_path).expanduser()
    return Path.home() / ".ai-fitness" / "config.json"


def read_config(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    return json.loads(path.read_text())


def write_config(path: Path, payload: dict[str, str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n")
    path.chmod(stat.S_IRUSR | stat.S_IWUSR)


def bundled_skills_dir() -> Path:
    package_dir = Path(__file__).resolve().parent
    packaged_skills = package_dir / "skills"
    if packaged_skills.exists():
        return packaged_skills
    repo_skills = package_dir.parent.parent / "skills"
    if repo_skills.exists():
        return repo_skills
    raise FileNotFoundError("bundled skills directory not found")


def available_skill_names() -> list[str]:
    return sorted(path.name for path in bundled_skills_dir().iterdir() if (path / "SKILL.md").is_file())


def get_skill_dir(skill_name: str) -> Path:
    skill_dir = bundled_skills_dir() / skill_name
    if not (skill_dir / "SKILL.md").is_file():
        available = ", ".join(available_skill_names())
        raise ValueError(f"unknown skill {skill_name!r}; available skills: {available}")
    return skill_dir


def bundled_skills() -> list[dict[str, str]]:
    return [
        {
            "name": name,
            "description": read_skill_description(get_skill_dir(name) / "SKILL.md"),
        }
        for name in available_skill_names()
    ]


def read_skill_description(skill_file: Path) -> str:
    in_frontmatter = False
    for line in skill_file.read_text().splitlines():
        if line == "---":
            if in_frontmatter:
                break
            in_frontmatter = True
            continue
        if in_frontmatter and line.startswith("description:"):
            return line.partition(":")[2].strip()
    return ""


def normalize_api_url(api_url: str) -> str:
    api_url = api_url.rstrip("/")
    if api_url.endswith("/v1"):
        api_url = api_url[:-3]
    if not api_url.startswith(("http://", "https://")):
        raise ValueError("api url must start with http:// or https://")
    return LEGACY_API_URLS.get(api_url, api_url)


def post_json(url: str, api_key: str, payload: dict[str, Any]) -> dict[str, Any]:
    return request_json(url, api_key, method="POST", payload=payload)


def get_json(url: str, api_key: str) -> dict[str, Any]:
    return request_json(url, api_key, method="GET")


def request_json(
    url: str,
    api_key: str,
    method: str,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    body = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = request.Request(
        url,
        data=body,
        method=method,
        headers={
            "Content-Type": "application/json",
            "X-API-Key": api_key,
            "User-Agent": "ai-fitness-cli/0.1.0",
        },
    )
    try:
        with request.urlopen(req, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except error.HTTPError as exc:
        body = exc.read().decode("utf-8")
        raise ValueError(format_remote_error(exc.code, body)) from exc


def format_remote_error(status_code: int, body: str) -> str:
    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        return f"remote API returned HTTP {status_code}: {body}"

    detail = payload.get("detail") if isinstance(payload, dict) else payload
    if isinstance(detail, str):
        return f"remote API returned HTTP {status_code}: {detail}"
    if isinstance(detail, list):
        return format_error_lines(status_code, "request failed", detail)
    if not isinstance(detail, dict):
        return f"remote API returned HTTP {status_code}: {json.dumps(payload)}"

    message = detail.get("message") or "request failed"
    errors = detail.get("errors") if isinstance(detail.get("errors"), list) else []
    return format_error_lines(status_code, message, errors)


def format_error_lines(status_code: int, message: str, errors: list[Any]) -> str:
    lines = [f"remote API returned HTTP {status_code}: {message}"]
    for item in errors:
        if not isinstance(item, dict):
            continue
        location = format_error_location(item.get("loc"))
        error_message = item.get("message") or item.get("msg") or "validation error"
        prefix = f"{location}: " if location else ""
        lines.append(f"- {prefix}{error_message}")
    return "\n".join(lines)


def format_error_location(loc: Any) -> str:
    if not isinstance(loc, list | tuple):
        return ""
    parts = [str(part) for part in loc if part is not None]
    return ".".join(parts)


if __name__ == "__main__":
    raise SystemExit(main())
