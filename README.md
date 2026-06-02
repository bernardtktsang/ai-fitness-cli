# AI Fitness CLI

Command line access to AI Fitness Buddy data for you and for shell-capable AI
agents.

The `fitness` command lets an agent read and write fitness data through the
hosted AI Fitness Buddy API without seeing your API key. You run `fitness login`
yourself; your agent runs normal shell commands after that.

## Quick Start

### Give This To Your Agent

Ask your agent to read this README, then give it this instruction:

```text
Install and configure AI Fitness CLI from:
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

List every AI Fitness skill bundled with the installed CLI:
fitness skills list

If you have a local skill repository, install all bundled AI Fitness skills into it:
fitness skills export --dest <your-skill-repository-path> --force

If you do not have a skill repository, read each listed skill directly:
fitness skills show <skill-name>
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

Open AI Health Sync on your iPhone, go to `Sync -> Agent Access`, create an
Agent API key, and paste it into the terminal prompt. Do not paste the key into
chat with an agent.

Check access:

```bash
fitness doctor
fitness context brief
```

## Useful Commands

```bash
fitness doctor
fitness context brief
fitness sync status
fitness health summary --start 2026-05-01 --end 2026-05-16
fitness meals list --start 2026-05-01 --end 2026-05-16
fitness foods search rice --json
fitness workouts list --start 2026-05-01T00:00:00+00:00 --end 2026-05-16T23:59:59+00:00
fitness progress show
fitness targets explain
```

For meal logging, timestamp fields are optional when the meal is being logged
right now. For a past or specific local meal time, use `local_eaten_at` plus
`eaten_at_timezone` in the meal JSON; use `eaten_at` only for an absolute
timestamp with an offset.

Use `fitness --help` or `fitness <command> --help` for the full command list.

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
export FITNESS_API_URL=https://api.bernardtktsangfitness.com
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
