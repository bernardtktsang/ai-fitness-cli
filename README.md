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

## Give This To Your Agent

Ask your agent to read this README, then give it this instruction:

```text
Install and configure AI Fitness CLI from:
https://github.com/bernardtktsang/ai-fitness-cli

Use shell/terminal commands.

Install with:
python3 -m pip install --user --upgrade git+https://github.com/bernardtktsang/ai-fitness-cli.git

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

The only secret step is `fitness login`; the user should run it in their own
terminal so the API key is never pasted into chat.

## Manual Setup

Use this flow when you are setting up the CLI yourself.

1. Install from the public GitHub repo:

```bash
python3 -m pip install --user --upgrade git+https://github.com/bernardtktsang/ai-fitness-cli.git
```

If you prefer an isolated tool install:

```bash
uv tool install git+https://github.com/bernardtktsang/ai-fitness-cli.git
pipx install git+https://github.com/bernardtktsang/ai-fitness-cli.git
```

2. Check it installed:

```bash
fitness --help
```

3. Log in from your own terminal:

```bash
fitness login
```

Open AI Health Sync on your iPhone, go to `Sync -> Agent Access`, create an
Agent API key, and paste it into the terminal prompt. Do not paste the key into
chat.

4. Verify access:

```bash
fitness doctor
fitness context brief
```

## Recommended Agent Setup

Use this flow when an agent will run the CLI for you.

Install the CLI:

```bash
python3 -m pip install --user --upgrade git+https://github.com/bernardtktsang/ai-fitness-cli.git
```

Then run the setup command yourself in your terminal:

```bash
fitness login
```

Create the Agent API key in AI Health Sync at `Sync -> Agent Access`, then paste
it into the terminal prompt. Do not paste the key into chat.

Then ask your agent to verify it:

```text
Check my AI Fitness CLI setup with `fitness doctor`, then get my current
fitness context with `fitness context brief`.
```

Agents often cannot safely handle hidden interactive prompts through their
terminal tool. Avoid pasting API keys into chat. Paste the key directly into
your own terminal.

Give your agent this instruction if it has not already read the top-level setup
prompt:

```text
Install and configure the AI Fitness CLI from:
https://github.com/bernardtktsang/ai-fitness-cli

Use shell/terminal commands. Do not ask me to paste my API key into chat.
If a key is needed, ask me to run the login command myself in my terminal.

After setup, use `fitness doctor` to verify access and `fitness context brief`
to get my current fitness context.

Run `fitness skills list` to discover every bundled AI Fitness skill.

If you have a local skill repository, install all bundled AI Fitness skills:
fitness skills export --dest <your-skill-repository-path> --force

If you do not have a skill repository, read each listed skill directly:
fitness skills show <skill-name>
```

## Hermes Setup

For Hermes, use the dedicated setup command. It logs the CLI in, adds a Hermes
memory note, enables the terminal tool for WhatsApp, and optionally restarts the
gateway.

```bash
python3 -m pip install --user --upgrade git+https://github.com/bernardtktsang/ai-fitness-cli.git

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

1. Install the CLI with `python3 -m pip install --user --upgrade git+...`.
2. Run `fitness login`.
3. Make sure the agent has shell/terminal command access.
4. Run `fitness skills list` so the agent sees every bundled skill.
5. Export all bundled skills into the agent's skill repository if it has one.
6. Add this instruction to the agent's memory, rules, or system context:

```text
For fitness, health, nutrition, meals, workouts, dashboard, targets, or progress
questions, use the shell command `fitness`.

Use `fitness doctor` to verify access.
Use `fitness context brief` for current context.
Run `fitness skills list` to see all bundled AI Fitness skills.
Install all bundled skills with `fitness skills export --dest <your-skill-repository-path> --force`
when you have a skill repository.
If the skills are not installed, read the relevant listed skill with `fitness skills show <skill-name>`
before handling meal logging, programme design, target, or nutrition review tasks.
Do not ask for API keys.
Do not print secrets or environment variables.
Use the CLI output to answer in plain language.
```

## Agent Skills

The installed CLI includes optional agent skill folders. Agents should run
`fitness skills list` after installing the CLI because that command is the source
of truth for every skill bundled with the current package.

Agents can use the skills in any of three generic ways:

1. Export all bundled skill folders into the agent's local skill repository.
2. Print and read each skill directly from the installed CLI.
3. Read or copy the source `skills/<name>` folders from a cloned repo.

List every bundled skill:

```bash
fitness skills list
```

Export all bundled skills:

```bash
fitness skills export --dest <your-skill-repository-path> --force
```

Export one skill:

```bash
fitness skills export --skill <skill-name> --dest <your-skill-repository-path> --force
```

Read a listed skill without exporting:

```bash
fitness skills show <skill-name>
```

If you are working from a cloned repo instead of the installed CLI, the same
skills live under `skills/`. Copy each folder in that directory into your
agent's skill repository, preserving the folder name and `SKILL.md` file.

Use the destination path for your own agent. The skills are plain folders, are
not tied to any one assistant runtime, and `fitness skills export` without
`--skill` installs all bundled skills.

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
fitness skills list
fitness skills export --dest <your-skill-repository-path> --force
fitness skills show <skill-name>
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
