#!/usr/bin/env bash
set -euo pipefail

API_URL="${FITNESS_API_URL:-}"
API_KEY="${FITNESS_API_KEY:-}"
FITNESS_BIN="${FITNESS_BIN:-fitness}"
HERMES_PLATFORM="whatsapp"
MEMORY_FILE="$HOME/.hermes/memories/USER.md"
SKIP_HERMES_MEMORY=0
SKIP_ENABLE_TERMINAL=0
RESTART_GATEWAY=0

usage() {
  cat <<'USAGE'
Configure a Hermes/agent machine to use the installed AI Fitness CLI.

Usage:
  configure-hermes-cli.sh --api-url URL --api-key afb_agent_...

Safer shell-history form:
  export FITNESS_API_KEY=afb_agent_...
  configure-hermes-cli.sh --api-url https://api.example.com

Options:
  --api-url URL              Public API URL, without /v1.
  --api-key KEY              User's afb_agent_... key. Can also use FITNESS_API_KEY.
  --fitness-bin PATH         CLI command/path. Defaults to fitness.
  --hermes-platform NAME     Hermes platform to enable terminal for. Defaults to whatsapp.
  --memory-file PATH         Hermes memory file. Defaults to ~/.hermes/memories/USER.md.
  --skip-hermes-memory       Do not append the Hermes instruction note.
  --skip-enable-terminal     Do not run hermes tools enable.
  --restart-gateway          Restart Hermes gateway after configuration.
  -h, --help                 Show this help.
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --api-url)
      API_URL="${2:-}"
      shift 2
      ;;
    --api-key)
      API_KEY="${2:-}"
      shift 2
      ;;
    --fitness-bin)
      FITNESS_BIN="${2:-}"
      shift 2
      ;;
    --hermes-platform)
      HERMES_PLATFORM="${2:-}"
      shift 2
      ;;
    --memory-file)
      MEMORY_FILE="${2:-}"
      shift 2
      ;;
    --skip-hermes-memory)
      SKIP_HERMES_MEMORY=1
      shift
      ;;
    --skip-enable-terminal)
      SKIP_ENABLE_TERMINAL=1
      shift
      ;;
    --restart-gateway)
      RESTART_GATEWAY=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

if [[ -z "$API_URL" ]]; then
  echo "Missing --api-url or FITNESS_API_URL." >&2
  exit 2
fi

if [[ -z "$API_KEY" ]]; then
  echo "Missing --api-key or FITNESS_API_KEY." >&2
  exit 2
fi

if [[ "$API_KEY" != afb_agent_* ]]; then
  echo "Expected an afb_agent_... key for Hermes/agent CLI access." >&2
  exit 2
fi

if ! command -v "$FITNESS_BIN" >/dev/null 2>&1; then
  echo "Could not find fitness CLI: $FITNESS_BIN" >&2
  echo "Install it first, for example: pipx install ai-fitness-cli" >&2
  exit 2
fi

"$FITNESS_BIN" login --api-url "$API_URL" --api-key "$API_KEY"

if [[ "$SKIP_HERMES_MEMORY" -eq 0 ]]; then
  mkdir -p "$(dirname "$MEMORY_FILE")"
  touch "$MEMORY_FILE"
  chmod 600 "$MEMORY_FILE"
  if ! grep -Fq "$FITNESS_BIN doctor" "$MEMORY_FILE"; then
    cat >> "$MEMORY_FILE" <<EOF

---
For fitness, health, nutrition, workout, dashboard, target, or progress questions, use the CLI command \`$FITNESS_BIN\`. It already has the remote API URL and agent key configured on this machine. Do not ask for API keys, do not print secret environment variables, and use the CLI output to answer in plain language. Useful commands include \`$FITNESS_BIN doctor\`, \`$FITNESS_BIN context brief\`, \`$FITNESS_BIN sync status\`, \`$FITNESS_BIN health summary --start YYYY-MM-DD --end YYYY-MM-DD\`, and \`$FITNESS_BIN meals list --start YYYY-MM-DD --end YYYY-MM-DD\`. For meal logging, omit timestamp fields when the user is logging a meal right now; use local_eaten_at plus eaten_at_timezone for past or specific local meal times. If you have a local skill repository, add the bundled AI Fitness skills with \`$FITNESS_BIN skills export --dest <your-skill-repository-path> --force\`. Otherwise read detailed workflows with \`$FITNESS_BIN skills show meal-logging\` and \`$FITNESS_BIN skills show fitness-program-design\`.
EOF
  fi
fi

if [[ "$SKIP_ENABLE_TERMINAL" -eq 0 ]]; then
  if command -v hermes >/dev/null 2>&1; then
    hermes tools enable --platform "$HERMES_PLATFORM" terminal
  else
    echo "Hermes CLI not found; skipped enabling terminal tool." >&2
  fi
fi

if [[ "$RESTART_GATEWAY" -eq 1 ]]; then
  if command -v hermes >/dev/null 2>&1; then
    hermes gateway restart
  else
    echo "Hermes CLI not found; skipped gateway restart." >&2
  fi
fi

echo "Configured Hermes to use: $FITNESS_BIN"
echo "Test with: $FITNESS_BIN doctor"
