from __future__ import annotations

import argparse
import os
import stat
import subprocess
import sys
from pathlib import Path

from ai_fitness_cli.cli import (
    API_KEY_ENV,
    API_URL_ENV,
    DEFAULT_API_URL,
    get_json,
    normalize_api_url,
    read_config,
    write_config,
)


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return configure(args)
    except (ValueError, OSError, subprocess.CalledProcessError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="fitness-configure-hermes",
        description="Configure Hermes to use the installed AI Fitness remote CLI.",
    )
    parser.add_argument("--api-url", default=os.environ.get(API_URL_ENV), help="Backend URL.")
    parser.add_argument(
        "--api-key",
        default=os.environ.get(API_KEY_ENV),
        help="User's afb_agent_... key. Can also use FITNESS_API_KEY.",
    )
    parser.add_argument("--config-file", help="Override fitness CLI config file.")
    parser.add_argument("--fitness-bin", default="fitness", help="CLI command Hermes should run.")
    parser.add_argument("--hermes-platform", default="whatsapp")
    parser.add_argument(
        "--memory-file",
        default=str(Path.home() / ".hermes" / "memories" / "USER.md"),
        help="Hermes built-in USER.md memory file.",
    )
    parser.add_argument("--skip-verify", action="store_true", help="Do not call the API first.")
    parser.add_argument("--skip-hermes-memory", action="store_true")
    parser.add_argument("--skip-enable-terminal", action="store_true")
    parser.add_argument("--restart-gateway", action="store_true")
    return parser


def configure(args: argparse.Namespace) -> int:
    config_path = Path(args.config_file).expanduser() if args.config_file else default_config_path()
    existing_config = read_config(config_path)
    api_url = args.api_url or existing_config.get("api_url") or DEFAULT_API_URL
    api_key = args.api_key or existing_config.get("api_key")
    if not api_key:
        raise ValueError("missing agent key; run `fitness login` first")
    if not api_key.startswith("afb_agent_"):
        raise ValueError("expected an afb_agent_... key for Hermes/agent CLI access")

    api_url = normalize_api_url(api_url)
    if not args.skip_verify:
        get_json(f"{api_url}/v1/agent/me", api_key)

    write_config(config_path, {"api_url": api_url, "api_key": api_key})

    if not args.skip_hermes_memory:
        write_memory_note(Path(args.memory_file).expanduser(), args.fitness_bin)

    if not args.skip_enable_terminal:
        run_if_available(
            [
                "hermes",
                "tools",
                "enable",
                "--platform",
                args.hermes_platform,
                "terminal",
            ],
            "Hermes CLI not found; skipped enabling terminal tool.",
        )

    if args.restart_gateway:
        run_if_available(["hermes", "gateway", "restart"], "Hermes CLI not found; skipped gateway restart.")

    print(f"saved fitness config: {config_path}")
    print(f"configured Hermes to use: {args.fitness_bin}")
    print(f"test with: {args.fitness_bin} doctor")
    return 0


def default_config_path() -> Path:
    return Path.home() / ".ai-fitness" / "config.json"


def write_memory_note(memory_file: Path, fitness_bin: str) -> None:
    memory_file.parent.mkdir(parents=True, exist_ok=True)
    memory_file.touch(exist_ok=True)
    memory_file.chmod(stat.S_IRUSR | stat.S_IWUSR)
    marker = f"{fitness_bin} doctor"
    if marker in memory_file.read_text():
        return
    with memory_file.open("a") as handle:
        handle.write(
            "\n---\n"
            "For fitness, health, nutrition, workout, dashboard, target, or progress questions, "
            f"use the CLI command `{fitness_bin}`. It already has the remote API URL and agent "
            "key configured on this machine. Do not ask for API keys, do not print secret "
            "environment variables, and use the CLI output to answer in plain language. Useful "
            f"commands include `{fitness_bin} doctor`, `{fitness_bin} context brief`, "
            f"`{fitness_bin} sync status`, `{fitness_bin} health summary --start YYYY-MM-DD "
            f"--end YYYY-MM-DD`, and `{fitness_bin} meals list --start YYYY-MM-DD "
            f"--end YYYY-MM-DD`. If you have a local skill repository, add the bundled AI "
            f"Fitness skills with `{fitness_bin} skills export --dest <your-skill-repository-path> "
            f"--force`. Otherwise read detailed workflows with `{fitness_bin} skills show "
            f"meal-logging` and `{fitness_bin} skills show fitness-program-design`.\n"
        )


def run_if_available(command: list[str], missing_message: str) -> None:
    executable = command[0]
    if not shutil_which(executable):
        print(missing_message, file=sys.stderr)
        return
    subprocess.run(command, check=True)


def shutil_which(executable: str) -> str | None:
    for path in os.environ.get("PATH", "").split(os.pathsep):
        candidate = Path(path) / executable
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return str(candidate)
    return None


if __name__ == "__main__":
    raise SystemExit(main())
