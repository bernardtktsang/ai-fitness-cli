# AI Fitness CLI

Remote-only command line client for AI Fitness Buddy agents and users.

## What This Does

`fitness` lets an agent such as Hermes, OpenClaw, or another shell-capable
assistant read and write fitness data through the hosted AI Fitness Buddy API.

The agent does not need direct access to the API key. It only needs permission
to run shell commands such as:

```bash
fitness context brief
fitness sync status
fitness meals list --start 2026-05-01 --end 2026-05-16
```

The CLI reads the API URL and key from its local config file.

## Quick Install

Install from the public GitHub repo:

```bash
uv tool install git+https://github.com/bernardtktsang/ai-fitness-cli.git
```

If you prefer `pipx`:

```bash
pipx install git+https://github.com/bernardtktsang/ai-fitness-cli.git
```

Check it installed:

```bash
fitness --help
```

## Recommended Agent Setup

Install the CLI:

```bash
uv tool install git+https://github.com/bernardtktsang/ai-fitness-cli.git
```

Then run the setup command yourself in your terminal:

```bash
fitness login
```

Open AI Health Sync on your iPhone, go to `Sync -> Agent Access`, create an
Agent API key, and paste it into the terminal prompt. Do not paste the key into
chat.

Then ask your agent to verify it:

```text
Check my AI Fitness CLI setup with `fitness doctor`, then get my current
fitness context with `fitness context brief`.
```

Agents often cannot safely handle hidden interactive prompts through their
terminal tool. Avoid pasting API keys into chat. Paste the key directly into
your own terminal.

Give your agent this instruction:

```text
Install and configure the AI Fitness CLI from:
https://github.com/bernardtktsang/ai-fitness-cli

Use shell/terminal commands. Do not ask me to paste my API key into chat.
If a key is needed, ask me to run the login command myself in my terminal.

After setup, use `fitness doctor` to verify access and `fitness context brief`
to get my current fitness context.
```

## Hermes Setup

For Hermes, use the dedicated setup command. It logs the CLI in, adds a Hermes
memory note, enables the terminal tool for WhatsApp, and optionally restarts the
gateway.

```bash
uv tool install git+https://github.com/bernardtktsang/ai-fitness-cli.git

fitness login
fitness hermes setup \
  --restart-gateway

fitness doctor
```

Run `fitness login` yourself in the Hermes machine terminal. Do not paste the
API key into a chat with the agent.

`fitness-configure-hermes` is also installed as a script-friendly alias for the
same setup flow:

```bash
fitness-configure-hermes \
  --api-url https://api.bernardtktsangfitness.com \
  --restart-gateway
```

## Generic Agent Setup

For agents other than Hermes:

1. Install the CLI with `uv tool install` or `pipx install`.
2. Run `fitness login`.
3. Make sure the agent has shell/terminal command access.
4. Add this instruction to the agent's memory, rules, or system context:

```text
For fitness, health, nutrition, meals, workouts, dashboard, targets, or progress
questions, use the shell command `fitness`.

Use `fitness doctor` to verify access.
Use `fitness context brief` for current context.
Do not ask for API keys.
Do not print secrets or environment variables.
Use the CLI output to answer in plain language.
```

## Agent Skills

This repo includes optional agent skill folders:

- `fitness-program-design`: programme design, macro targets, phase targets,
  hybrid training plans, and injury-aware replanning.
- `meal-logging`: meal estimation, logging, corrections, confirmations, and
  target review.

Agents can use them in either of two generic ways:

1. Read the relevant `skills/<name>/SKILL.md` file directly from a cloned or
   downloaded copy of this repo.
2. Copy the whole `skills/<name>` folder into whatever local skill directory
   that agent supports.

Example:

```bash
git clone https://github.com/bernardtktsang/ai-fitness-cli.git
cp -R ai-fitness-cli/skills/meal-logging ~/.codex/skills/
```

Use the destination path for your own agent. The skills are plain folders, so
they are not tied to the `fitness` executable or to any one assistant runtime.

## Manual Login

```bash
fitness login
```

`fitness login` defaults to `https://api.bernardtktsangfitness.com`, validates
the Agent API key with the hosted API, and stores it locally. Advanced/dev usage
can still pass `--api-url` and `--api-key`.

The key is stored in:

```text
~/.ai-fitness/config.json
```

The file is written with `0600` permissions so only the local user can read it.
Environment variables override the config:

```bash
export FITNESS_API_URL=https://api.bernardtktsangfitness.com
export FITNESS_API_KEY=afb_agent_...
```

## Useful Commands

```bash
fitness doctor
fitness context brief
fitness sync status
fitness health summary --start 2026-05-01 --end 2026-05-16
fitness meals list --start 2026-05-01 --end 2026-05-16
fitness progress show
fitness targets explain
```

## Troubleshooting

If `fitness` is not found, make sure `~/.local/bin` is on PATH:

```bash
export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"
```

If login succeeds but an agent cannot use it, the agent probably does not have
shell/terminal access enabled.
