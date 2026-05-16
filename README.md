# AI Fitness CLI

Remote-only command line client for AI Fitness Buddy.

This package contains only the user/agent CLI. It does not include the backend,
database models, migrations, iOS app, deployment scripts, MCP server, or private
operator commands.

## Install

From this local checkout:

```bash
pipx install /Users/bernardtsang/APP/ai-fitness-cli
```

Later, from a clean public Git repo:

```bash
pipx install git+https://github.com/YOUR_ORG/ai-fitness-cli.git
```

## Login

```bash
fitness login \
  --api-url https://api.bernardtktsangfitness.com \
  --api-key afb_agent_...
```

The key is stored in `~/.config/ai-fitness-cli/config.json` with `0600`
permissions. Environment variables override the config:

```bash
export FITNESS_API_URL=https://api.bernardtktsangfitness.com
export FITNESS_API_KEY=afb_agent_...
```

## Use

```bash
fitness doctor
fitness context brief
fitness sync status
fitness health summary --start 2026-05-01 --end 2026-05-16
fitness meals list --start 2026-05-01 --end 2026-05-16
```

## Configure Hermes

On the user's Hermes machine, use the installed helper command:

```bash
export FITNESS_API_KEY=afb_agent_...
fitness hermes setup \
  --api-url https://api.bernardtktsangfitness.com \
  --restart-gateway
unset FITNESS_API_KEY
```

The helper logs the CLI in, adds a Hermes memory note, enables the terminal
tool for WhatsApp, and optionally restarts the gateway.

If you are working from a source checkout before packaging, the equivalent shell
script is also available:

```bash
scripts/configure-hermes-cli.sh --api-url https://api.bernardtktsangfitness.com
```

The package also installs `fitness-configure-hermes` as a script-friendly alias
for the same setup flow.

## Not Included

This package intentionally does not include:

- admin user/key commands
- database access
- backend server code
- MCP server code
- migrations
- deployment scripts
- private product docs
