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
DEFAULT_API_URL = "https://api.bernardtktsangfitness.com"


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
        description="Remote-only CLI for AI Fitness Buddy agents and users.",
    )
    subparsers = parser.add_subparsers(dest="command")

    add_login_commands(subparsers)
    add_hermes_commands(subparsers)
    add_skill_commands(subparsers)
    add_doctor_command(subparsers)
    add_context_commands(subparsers)
    add_progress_commands(subparsers)
    add_health_commands(subparsers)
    add_workout_commands(subparsers)
    add_sync_commands(subparsers)
    add_profile_commands(subparsers)
    add_meal_commands(subparsers)
    add_food_commands(subparsers)
    add_projection_commands(subparsers)
    add_programme_commands(subparsers)
    add_target_commands(subparsers)
    add_recommendation_commands(subparsers)
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


def set_remote(parser: argparse.ArgumentParser, command_path: str) -> None:
    parser.set_defaults(handler=handle_remote_command, remote_command=command_path)


def add_login_commands(subparsers: argparse._SubParsersAction) -> None:
    login = subparsers.add_parser("login", help="Connect this machine to AI Health Sync.")
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


def add_context_commands(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser("context", help="Compact agent-ready context.")
    nested = parser.add_subparsers(dest="context_command", required=True)
    brief = nested.add_parser("brief", help="Show compact dashboard context.")
    brief.add_argument("--as-of", help="ISO date. Defaults to today in user timezone.")
    add_common_output(brief)
    set_remote(brief, "context.brief")


def add_progress_commands(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser("progress", help="Plan progress calculations.")
    nested = parser.add_subparsers(dest="progress_command", required=True)
    show = nested.add_parser("show", help="Show weekly plan progress.")
    show.add_argument("--week-start", help="ISO date.")
    show.add_argument("--week-end", help="ISO date.")
    show.add_argument("--as-of", help="ISO date. Defaults to today in user timezone.")
    add_common_output(show)
    set_remote(show, "progress.show")


def add_health_commands(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser("health", help="Health, body, and catalog reads.")
    nested = parser.add_subparsers(dest="health_command", required=True)

    summary = nested.add_parser("summary", help="Daily structured health summaries.")
    summary.add_argument("--start", required=True, help="ISO start date.")
    summary.add_argument("--end", required=True, help="ISO end date.")
    add_common_output(summary)
    set_remote(summary, "health.summary")

    samples = nested.add_parser("samples", help="Granular health samples.")
    samples.add_argument("--metrics", required=True, help="Comma-separated metric names.")
    samples.add_argument("--start", required=True, help="ISO start date/datetime. Naive values use the user timezone.")
    samples.add_argument("--end", required=True, help="ISO end date/datetime. Naive values use the user timezone.")
    samples.add_argument("--limit", type=int, default=100)
    add_timezone_override(samples)
    add_common_output(samples)
    set_remote(samples, "health.samples")

    body = nested.add_parser("body", help="Body composition measurements.")
    body.add_argument("--metrics", help="Comma-separated body metric names.")
    body.add_argument("--start", help="ISO start date/datetime. Naive values use the user timezone.")
    body.add_argument("--end", help="ISO end date/datetime. Naive values use the user timezone.")
    body.add_argument("--limit", type=int, default=100)
    add_timezone_override(body)
    add_common_output(body)
    set_remote(body, "health.body")

    catalog = nested.add_parser("catalog", help="Supported, available, missing, and stale metrics.")
    catalog.add_argument("--stale-after-hours", type=int, default=24)
    add_common_output(catalog)
    set_remote(catalog, "health.catalog")


def add_workout_commands(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser("workouts", help="Workout reads.")
    nested = parser.add_subparsers(dest="workout_command", required=True)
    list_cmd = nested.add_parser("list", help="List workouts in a time range.")
    list_cmd.add_argument("--start", required=True, help="ISO start date/datetime. Naive values use the user timezone.")
    list_cmd.add_argument("--end", required=True, help="ISO end date/datetime. Naive values use the user timezone.")
    list_cmd.add_argument("--limit", type=int, default=100)
    add_timezone_override(list_cmd)
    add_common_output(list_cmd)
    set_remote(list_cmd, "workouts.list")


def add_sync_commands(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser("sync", help="Sync status.")
    nested = parser.add_subparsers(dest="sync_command", required=True)
    status = nested.add_parser("status", help="Show health data sync status.")
    status.add_argument("--stale-after-hours", type=int, default=24)
    add_timezone_override(status)
    add_common_output(status)
    set_remote(status, "sync.status")


def add_profile_commands(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser("profile", help="User profile reads/writes.")
    nested = parser.add_subparsers(dest="profile_command", required=True)
    show = nested.add_parser("show", help="Show user profile.")
    add_common_output(show)
    set_remote(show, "profile.show")

    update = nested.add_parser("update", help="Merge profile JSON.")
    add_json_input(update, "profile")
    add_common_output(update)
    set_remote(update, "profile.update")


def add_meal_commands(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser("meals", help="Nutrition meal reads/writes.")
    nested = parser.add_subparsers(dest="meal_command", required=True)

    summary = nested.add_parser("summary", help="Daily nutrition totals.")
    summary.add_argument("--start", required=True, help="ISO start date.")
    summary.add_argument("--end", required=True, help="ISO end date.")
    add_timezone_override(summary)
    add_common_output(summary)
    set_remote(summary, "meals.summary")

    list_cmd = nested.add_parser("list", help="List meal logs.")
    list_cmd.add_argument("--start", required=True, help="ISO start date.")
    list_cmd.add_argument("--end", required=True, help="ISO end date.")
    list_cmd.add_argument("--limit", type=int, default=50)
    add_timezone_override(list_cmd)
    add_common_output(list_cmd)
    set_remote(list_cmd, "meals.list")

    save = nested.add_parser(
        "save",
        help=(
            "Save a meal log from JSON. Omit eaten_at for just-now meals; "
            "use eaten_at plus timezone for specified local meal times."
        ),
    )
    add_json_input(save, "meal", file_aliases=("--file",))
    add_timezone_override(save)
    add_common_output(save)
    set_remote(save, "meals.save")

    update = nested.add_parser("update", help="Update a meal log from JSON.")
    update.add_argument("--meal-id", required=True)
    add_json_input(update, "meal_update", file_aliases=("--file",))
    add_timezone_override(update)
    add_common_output(update)
    set_remote(update, "meals.update")

    delete = nested.add_parser("delete", help="Delete a meal log.")
    delete.add_argument("--meal-id", required=True)
    add_common_output(delete)
    set_remote(delete, "meals.delete")


def add_food_filters(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--start", help="ISO start date.")
    parser.add_argument("--end", help="ISO end date.")
    parser.add_argument("--meal-type", choices=("breakfast", "lunch", "dinner", "snack"))
    parser.add_argument(
        "--status",
        choices=("all", "confirmed", "provisional", "complete"),
        default="all",
        help="Meal status filter. Defaults to all.",
    )


def add_food_commands(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser("foods", help="Personal food history lookups.")
    nested = parser.add_subparsers(dest="food_command", required=True)

    search = nested.add_parser("search", help="Search prior logged food items.")
    search.add_argument("query")
    search.add_argument("--limit", type=int, default=10)
    search.add_argument("--entry-limit", type=int, default=3)
    add_food_filters(search)
    add_timezone_override(search)
    add_common_output(search)
    set_remote(search, "foods.search")

    list_cmd = nested.add_parser("list", help="List unique prior logged food items.")
    list_cmd.add_argument("--limit", type=int, default=50)
    add_food_filters(list_cmd)
    add_timezone_override(list_cmd)
    add_common_output(list_cmd)
    set_remote(list_cmd, "foods.list")

    history = nested.add_parser("history", help="Show capped history for one food item.")
    history.add_argument("name")
    history.add_argument("--limit", type=int, default=20)
    add_food_filters(history)
    add_timezone_override(history)
    add_common_output(history)
    set_remote(history, "foods.history")

    get = nested.add_parser("get", help="Get recent reference entries for one food item.")
    get.add_argument("name")
    get.add_argument("--limit", type=int, default=5)
    add_food_filters(get)
    add_timezone_override(get)
    add_common_output(get)
    set_remote(get, "foods.get")


def add_projection_commands(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser("projections", help="Dashboard projections.")
    nested = parser.add_subparsers(dest="projection_command", required=True)

    list_cmd = nested.add_parser("list", help="List dashboard projections.")
    list_cmd.add_argument("--type", dest="projection_type")
    list_cmd.add_argument("--limit", type=int, default=20)
    add_common_output(list_cmd)
    set_remote(list_cmd, "projections.list")

    show = nested.add_parser("show", help="Show a dashboard projection.")
    show.add_argument("--projection-id", required=True)
    add_common_output(show)
    set_remote(show, "projections.show")

    deactivate = nested.add_parser("deactivate", help="Mark a dashboard projection inactive.")
    deactivate.add_argument("--projection-id", required=True)
    deactivate.add_argument("--status", default="inactive")
    deactivate.add_argument("--agent-run-id")
    add_common_output(deactivate)
    set_remote(deactivate, "projections.deactivate")

    delete = nested.add_parser("delete", help="Delete a dashboard projection.")
    delete.add_argument("--projection-id", required=True)
    add_common_output(delete)
    set_remote(delete, "projections.delete")


def add_programme_commands(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser("programme", help="Programme writes.")
    nested = parser.add_subparsers(dest="programme_command", required=True)
    save = nested.add_parser("save", help="Save active programme.")
    save.add_argument("--name", required=True)
    save.add_argument("--start", required=True, help="ISO start date.")
    save.add_argument("--end", required=True, help="ISO end date.")
    save.add_argument("--goal", required=True)
    save.add_argument("--agent-run-id")
    add_json_input(save, "payload", required=False)
    add_common_output(save)
    set_remote(save, "programme.save")


def add_target_commands(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser("targets", help="Target planning reads/writes.")
    nested = parser.add_subparsers(dest="target_command", required=True)

    validate = nested.add_parser("validate", help="Validate a flat target map.")
    add_json_input(validate, "targets")
    set_remote(validate, "targets.validate")

    explain = nested.add_parser("explain", help="Explain active target layers for a date.")
    explain.add_argument("--as-of", help="ISO date. Defaults to today in user timezone.")
    add_common_output(explain)
    set_remote(explain, "targets.explain")

    phase = nested.add_parser("phase", help="Phase target commands.")
    phase_nested = phase.add_subparsers(dest="target_phase_command", required=True)
    phase_save = phase_nested.add_parser("save", help="Save phase daily target template.")
    phase_save.add_argument("--phase-name", required=True)
    phase_save.add_argument("--start", required=True, help="ISO start date.")
    phase_save.add_argument("--end", required=True, help="ISO end date.")
    phase_save.add_argument("--status", default="active")
    phase_save.add_argument("--programme-id")
    phase_save.add_argument("--rationale")
    phase_save.add_argument("--agent-run-id")
    add_json_input(phase_save, "targets")
    add_json_input(phase_save, "weekly_overrides", required=False)
    add_json_input(phase_save, "payload", required=False)
    add_common_output(phase_save)
    set_remote(phase_save, "targets.phase.save")

    schedule = nested.add_parser("schedule", help="Target schedule commands.")
    schedule_nested = schedule.add_subparsers(dest="target_schedule_command", required=True)
    schedule_save = schedule_nested.add_parser("save", help="Save repeating target schedule.")
    schedule_save.add_argument("--start", required=True, help="ISO start date.")
    schedule_save.add_argument("--end", required=True, help="ISO end date.")
    schedule_save.add_argument("--status", default="active")
    schedule_save.add_argument("--name")
    schedule_save.add_argument("--phase-name")
    schedule_save.add_argument("--programme-id")
    schedule_save.add_argument("--rationale")
    schedule_save.add_argument("--agent-run-id")
    add_json_input(schedule_save, "default_targets", required=False)
    add_json_input(schedule_save, "weekday_targets", required=False)
    add_json_input(schedule_save, "date_overrides", required=False)
    add_json_input(schedule_save, "payload", required=False)
    add_common_output(schedule_save)
    set_remote(schedule_save, "targets.schedule.save")

    schedule_list = schedule_nested.add_parser("list", help="List target schedules.")
    schedule_list.add_argument("--limit", type=int, default=20)
    add_common_output(schedule_list)
    set_remote(schedule_list, "targets.schedule.list")

    schedule_show = schedule_nested.add_parser("show", help="Show one target schedule.")
    schedule_show.add_argument("--projection-id", required=True)
    add_common_output(schedule_show)
    set_remote(schedule_show, "targets.schedule.show")

    schedule_update = schedule_nested.add_parser("update", help="Update a target schedule payload.")
    schedule_update.add_argument("--projection-id", required=True)
    schedule_update.add_argument("--start", help="ISO start date.")
    schedule_update.add_argument("--end", help="ISO end date.")
    schedule_update.add_argument("--status")
    schedule_update.add_argument("--name")
    schedule_update.add_argument("--phase-name")
    schedule_update.add_argument("--programme-id")
    schedule_update.add_argument("--rationale")
    schedule_update.add_argument("--agent-run-id")
    add_json_input(schedule_update, "default_targets", required=False)
    add_json_input(schedule_update, "weekday_targets", required=False)
    add_json_input(schedule_update, "date_overrides", required=False)
    add_json_input(schedule_update, "payload", required=False)
    add_common_output(schedule_update)
    set_remote(schedule_update, "targets.schedule.update")

    schedule_deactivate = schedule_nested.add_parser(
        "deactivate", help="Mark a target schedule inactive."
    )
    schedule_deactivate.add_argument("--projection-id", required=True)
    schedule_deactivate.add_argument("--status", default="inactive")
    schedule_deactivate.add_argument("--agent-run-id")
    add_common_output(schedule_deactivate)
    set_remote(schedule_deactivate, "targets.schedule.deactivate")

    schedule_delete = schedule_nested.add_parser("delete", help="Delete a target schedule.")
    schedule_delete.add_argument("--projection-id", required=True)
    add_common_output(schedule_delete)
    set_remote(schedule_delete, "targets.schedule.delete")

    daily = nested.add_parser("daily", help="Daily target override commands.")
    daily_nested = daily.add_subparsers(dest="target_daily_command", required=True)
    daily_save = daily_nested.add_parser("save", help="Save one date-specific target override.")
    daily_save.add_argument("--date", required=True, help="ISO target date.")
    daily_save.add_argument("--status", default="draft")
    daily_save.add_argument("--week-start", help="ISO date.")
    daily_save.add_argument("--week-end", help="ISO date.")
    daily_save.add_argument("--rationale")
    daily_save.add_argument("--agent-run-id")
    add_json_input(daily_save, "targets")
    add_json_input(daily_save, "payload", required=False)
    add_common_output(daily_save)
    set_remote(daily_save, "targets.daily.save")


def add_recommendation_commands(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser("recommendation", help="Dashboard recommendation writes.")
    nested = parser.add_subparsers(dest="recommendation_command", required=True)
    write = nested.add_parser("write", help="Write dashboard recommendation.")
    write.add_argument("--message", required=True)
    write.add_argument("--title")
    write.add_argument("--priority", default="normal")
    write.add_argument("--recommendation-date", help="ISO date.")
    write.add_argument("--valid-until", help="ISO datetime. Naive values use the user timezone.")
    write.add_argument("--agent-run-id")
    add_json_input(write, "payload", required=False)
    add_common_output(write)
    set_remote(write, "recommendation.write")


def add_dashboard_commands(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser("dashboard", help="Dashboard preferences.")
    nested = parser.add_subparsers(dest="dashboard_command", required=True)
    metrics = nested.add_parser("metrics", help="Dashboard target metric display order.")
    metrics_nested = metrics.add_subparsers(dest="dashboard_metrics_command", required=True)
    set_cmd = metrics_nested.add_parser("set", help="Set synced Today/Week target metrics.")
    set_cmd.add_argument("--today", required=True, help="Comma-separated metric keys.")
    set_cmd.add_argument("--week", required=True, help="Comma-separated metric keys.")
    set_cmd.add_argument("--updated-by", default="agent")
    set_cmd.add_argument("--updated-at", help="ISO datetime. Naive values use the user timezone.")
    add_common_output(set_cmd)
    set_remote(set_cmd, "dashboard.metrics.set")


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
    return 0


def handle_remote_command(args: argparse.Namespace) -> int:
    api_url, api_key, _ = get_credentials()
    payload = {
        "command": args.remote_command,
        "args": remote_args_from_namespace(args),
    }
    response = post_json(f"{api_url}/v1/agent/commands", api_key, payload)
    stdout = response.get("stdout") or ""
    if stdout:
        print(stdout, end="" if stdout.endswith("\n") else "\n")
    return int(response.get("exit_code") or 0)


def remote_args_from_namespace(args: argparse.Namespace) -> dict[str, Any]:
    values: dict[str, Any] = {}
    for key, value in vars(args).items():
        if key in {"handler", "remote_command"} or callable(value):
            continue
        if key.endswith("_file") and value is not None:
            json_key = f"{key[:-5]}_json"
            values[json_key] = Path(value).read_text()
            values[key] = None
            continue
        values[key] = value
    return values


def prompt_for_agent_key() -> str:
    print(
        "Open AI Health Sync on your iPhone:\n"
        "Sync -> Agent Access -> Create Agent Key\n\n"
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
    return api_url


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
