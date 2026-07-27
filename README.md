# Ascent AI CLI

Command-line access to Ascent AI data for you and for shell-capable AI
agents.

The `fitness` command lets an agent read and write fitness data through the
hosted Ascent AI API without seeing your API key. You run `fitness login`
yourself; your agent runs normal shell commands after that.

For the durable operating workflow after setup, read
[docs/byo-agent-operator-guide.md](docs/byo-agent-operator-guide.md).

## Quick Start

### Give This To Your Agent

Ask your agent to read this README, then give it this instruction:

```text
Install and configure Ascent AI CLI from:
https://github.com/bernardtktsang/ai-fitness-cli

Use shell/terminal commands.

Install with:
uv tool install git+https://github.com/bernardtktsang/ai-fitness-cli.git

If uv is not available, install with pipx instead:
pipx install git+https://github.com/bernardtktsang/ai-fitness-cli.git

Do not ask me to paste API keys into chat.
If login is needed, ask me to run `fitness login` myself in my terminal.

After I finish login, run:
fitness doctor
fitness context brief

List every Ascent AI skill bundled with the installed CLI:
fitness skills list

If you have a local skill repository, install all bundled Ascent AI skills into it:
fitness skills export --dest <your-skill-repository-path> --force

If you do not have a skill repository, read each listed skill directly:
fitness skills show <skill-name>

After setup, use this operator guide for the day-to-day agent workflow:
https://github.com/bernardtktsang/ai-fitness-cli/blob/main/docs/byo-agent-operator-guide.md
```

### Manual Setup

Use this if you are setting up the CLI yourself.

Check what install tools are available:

```bash
command -v python3 pip3 uv pipx
```

Install with `uv`:

```bash
uv tool install git+https://github.com/bernardtktsang/ai-fitness-cli.git
```

Or install with `pipx`:

```bash
pipx install git+https://github.com/bernardtktsang/ai-fitness-cli.git
```

If neither is available, use a manual venv:

```bash
python3 -m venv ~/.local/share/ai-fitness-cli
source ~/.local/share/ai-fitness-cli/bin/activate
pip install --upgrade git+https://github.com/bernardtktsang/ai-fitness-cli.git
mkdir -p ~/.local/bin
ln -sf ~/.local/share/ai-fitness-cli/bin/fitness ~/.local/bin/fitness
```

Verify the command:

```bash
fitness --help
```

Log in from your own terminal:

```bash
fitness login
```

Open Ascent AI on your iPhone, go to `Settings -> AI Agent`, generate an Agent
API key, and paste it into the terminal prompt. Do not paste the key into chat
with an agent.

Check access:

```bash
fitness doctor
fitness context brief
```

## Useful Commands

```bash
fitness doctor
fitness context brief
fitness context trend --weeks 4
fitness sync status
fitness health summary --start 2026-05-01 --end 2026-05-16
fitness meals list --start 2026-05-01 --end 2026-05-16
fitness foods search rice --json
fitness nutrition lookup "char siu rice" --portion-hint "one plate" --json
fitness workouts list --start 2026-05-01 --end 2026-05-16
fitness workouts save --file /tmp/workout.json --json
fitness programme list
fitness dashboard metrics show
fitness progress show
fitness targets explain
```

For meal logging, omit `eaten_at` when the meal is being logged right now. For a past or specific local meal time, use `eaten_at` as a local naive datetime plus `timezone`, for example `{"eaten_at": "2026-06-06T19:30:00", "timezone": "Asia/Hong_Kong"}`. Offset-only `eaten_at` is accepted, but do not combine an offset datetime with `timezone`.

CLI date/datetime input uses the backend user timezone by default when no offset is supplied. Supported timestamped commands also accept `--timezone IANA/Name` as an input/display override, for example `fitness workouts list --start 2026-05-01 --end 2026-05-16 --timezone Asia/Hong_Kong`. Do not combine offset datetimes with an explicit timezone.

Use `fitness --help` or `fitness <command> --help` for the full command list.


## Update Log

Keep this section updated whenever CLI behavior, bundled skills, examples, or
backend-facing command contracts change.

### 2026-07-27 - Ascent AI branding and production API

- Updated user-facing CLI, documentation, and bundled skill branding from AI
  Fitness Buddy / AI Health Sync to Ascent AI.
- Changed the default production backend to
  `https://api.ascent-ai-fitness-coach.com`.
- Existing configs that contain the former production URL are migrated at
  request time; custom and self-hosted backend URLs are unchanged.
- Updated login guidance to the current iOS path: `Settings -> AI Agent`.

### 2026-06-20 - Agent workout write

- Added `fitness workouts save`, mapping to the backend `workouts.save` agent
  command for agent-logged workouts (insert-only).
- The JSON body takes `workout_type`, `start_time`, and `end_time` (required)
  plus optional duration, energy, distance, heart-rate, and `notes` fields.
  Timestamps follow the `meals save` rule; do not combine an offset with
  `--timezone`.
- Provenance and identity fields (`source_name`, `source_bundle_id`,
  `external_uuid`, `metadata`) are set server-side and must not be sent.
- Documented the write in the `fitness-program-design` skill and added CLI tests.

### 2026-06-20 - Coaching best-practices skill

- Added the bundled `coaching-best-practices` skill: summarize progress and
  encourage when on track (reusing the enriched `fitness context brief`), propose
  habit stacking at plan setup, and ask the user their self-chosen reward.
- The skill reuses existing allowlisted `fitness` commands and adds no new tool
  surface; reward and habit-stack choices are unstructured agent-memory context,
  not backend writes.
- Updated the operator guide skill list and CLI tests to cover the new skill.

### 2026-06-05 - Strict itemized meal writes

- Updated meal logging guidance so `meals save` and item-replacement
  `meals update` use complete item-level nutrition.
- Agents should send `items` with `calories`, `protein_g`, `carbs_g`, and
  `fat_g` on each item.
- Agents should not send meal-level nutrition fields such as `calories`,
  `total_calories`, `protein_g`, `carbs_g`, or `fat_g`.
- Updated bundled meal logging skills and CLI test fixtures to match the new
  backend write contract.

## Agent Skills

The CLI includes optional skill folders for agents. List them with:

```bash
fitness skills list
```

Read a skill directly:

```bash
fitness skills show <skill-name>
```

Export all skills into an agent skill repository:

```bash
fitness skills export --dest <your-skill-repository-path> --force
```

## Hermes

For Hermes, install the CLI, log in yourself, then run:

```bash
fitness hermes setup \
  --restart-gateway

fitness doctor
```

`fitness-configure-hermes` is also installed as a script-friendly alias for the
same setup flow.

## Config and Secrets

`fitness login` stores the Agent API key in:

```text
~/.ai-fitness/config.json
```

The file is written with `0600` permissions. Environment variables override the
config:

```bash
export FITNESS_API_URL=https://api.ascent-ai-fitness-coach.com
export FITNESS_API_KEY=afb_agent_...
```

## Troubleshooting

### `externally-managed-environment`

Your Python install is managed by the operating system or package manager. Use
`uv` or `pipx` instead of direct pip installs.

If you understand the risk and specifically need a user-level pip install on a
Debian/Ubuntu system, this may work:

```bash
python3 -m pip install --user --break-system-packages --upgrade \
  git+https://github.com/bernardtktsang/ai-fitness-cli.git
```

### `No module named pip`

```bash
sudo apt install python3-pip
```

### `fitness: command not found`

Make sure `~/.local/bin` and `~/.cargo/bin` are on PATH:

```bash
export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"
```

Add that line to `~/.bashrc` or `~/.zshrc` if you want it to persist.

### Agent cannot run `fitness`

If login succeeds but an agent cannot use the CLI, the agent probably does not
have shell or terminal access enabled.
