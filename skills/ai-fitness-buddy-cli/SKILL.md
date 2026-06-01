---
name: ai-fitness-buddy-cli
description: Use when working with the AI Fitness Buddy CLI `fitness`, including setup, login, remote API connectivity, command reference, meal logging, meal updates, workouts, health data, targets, programmes, projections, dashboard metrics, JSON schemas, and common validation pitfalls.
---

# AI Fitness Buddy CLI

Use this skill as the command and schema reference for the remote-only AI Fitness Buddy CLI.

## Default Workflow

1. Run `fitness doctor` when setup, auth, API URL, or credential state is uncertain.
2. Use `--json` for commands whose output will be parsed programmatically.
3. For structured writes, create a temporary JSON file and pass it with the relevant `--file` or `--*-file` flag.
4. For meals being logged right now, omit timestamp fields and let the backend stamp the save time. For past/specific local meal times, use `local_eaten_at` plus `eaten_at_timezone`; use offset datetimes for health/workout ranges and absolute meal times.
5. After remote writes, read back the relevant resource when correctness matters.

Destructive commands such as `fitness meals delete`, `fitness projections delete`, and `fitness targets schedule delete` mutate remote data. Confirm intent unless the user explicitly asked for the deletion.

## Installation And Login

Install or refresh the CLI:

```bash
uv tool install --force git+https://github.com/bernardtktsang/ai-fitness-cli.git
```

Verify setup:

```bash
fitness doctor
fitness doctor --json
```

Expected setup output includes `mode=remote`, `api_url`, and credential details. If credentials are missing, run:

```bash
fitness login
```

If commands fail while referencing old local paths, reinstall with `--force`.

## Quick Reference

Daily status:

```bash
fitness context brief --json
fitness targets explain --as-of YYYY-MM-DD --json
```

Meals:

```bash
fitness meals summary --start YYYY-MM-DD --end YYYY-MM-DD --json
fitness meals list --start YYYY-MM-DD --end YYYY-MM-DD --json
fitness meals save --file /tmp/meal.json --json
fitness meals update --meal-id <uuid> --file /tmp/meal.json --json
fitness meals delete --meal-id <uuid> --json
```

The generated long-form file flags are also valid: `--meal-file` for `meals save` and `--meal-update-file` for `meals update`.

Health and workouts:

```bash
fitness health summary --start YYYY-MM-DD --end YYYY-MM-DD --json
fitness health body --json
fitness health catalog --json
fitness health samples --metrics steps,heart_rate --start DATETIME --end DATETIME --json
fitness workouts list --start DATETIME --end DATETIME --json
fitness sync status --json
```

Targets and programmes:

```bash
fitness targets validate --targets-file /tmp/t.json
fitness targets phase save --phase-name "Name" --start YYYY-MM-DD --end YYYY-MM-DD --targets-file /tmp/t.json --json
fitness targets schedule save --start YYYY-MM-DD --end YYYY-MM-DD --default-targets-file /tmp/d.json --weekday-targets-file /tmp/w.json --json
fitness targets schedule list --json
fitness targets schedule show --projection-id <uuid> --json
fitness targets daily save --date YYYY-MM-DD --targets-file /tmp/d.json --json
fitness programme save --name "Name" --start YYYY-MM-DD --end YYYY-MM-DD --goal "..." --payload-file /tmp/p.json --json
fitness progress show --json
fitness projections list --json
fitness projections show --projection-id <uuid> --json
fitness projections deactivate --projection-id <uuid> --json
fitness projections delete --projection-id <uuid> --json
```

Profile and dashboard:

```bash
fitness profile show --json
fitness profile update --profile-file /tmp/profile.json --json
fitness dashboard metrics set --today calories,protein_g,steps --week calories,protein_g,steps --json
```

Config and bundled skills:

```bash
fitness config show --json
fitness skills list --json
fitness skills show ai-fitness-buddy-cli
fitness skills export --dest /path/to/skills
```

## Meal JSON

Use only the backend's accepted flat keys. Do not send nested `macros`, `nutrients`, `nutrition`, or similar objects.

Example:

```json
{
  "local_eaten_at": "2026-05-31T12:00:00",
  "eaten_at_timezone": "Asia/Hong_Kong",
  "meal_type": "lunch",
  "items": [
    {
      "name": "Chicken rice",
      "portion_description": "1 plate",
      "calories": 620,
      "protein_g": 34,
      "carbs_g": 72,
      "fat_g": 22,
      "confidence": 0.75
    }
  ],
  "total_calories": 620,
  "notes": "estimated from user description",
  "source": "agent"
}
```

Item-level fields:

- `name` (string, required)
- `calories` (number)
- `protein_g` (number)
- `carbs_g` (number)
- `fat_g` (number)
- `fiber_g` (number)
- `sugar_g` (number)
- `sodium_mg` (number)
- `saturated_fat_g` (number)
- `caffeine_mg` (number)
- `water_ml` (number)
- `portion_description` (string)
- `confidence` (float from 0.0 to 1.0)

Meal-level fields:

- `eaten_at` (ISO 8601 datetime with offset, optional absolute timestamp)
- `local_eaten_at` (ISO 8601 datetime without offset, optional local meal time)
- `eaten_at_timezone` (IANA timezone such as `Asia/Hong_Kong`, used with `local_eaten_at`)
- `meal_type` (`breakfast`, `lunch`, `dinner`, or `snack`)
- `items` (array, required)
- `total_calories` (number, sum of item calories)
- `notes` (string)
- `source` (string)

- If the meal is being logged right now, omit `eaten_at`, `local_eaten_at`, and `eaten_at_timezone`; the backend records the save time.
- If the user specifies a local time, prefer `local_eaten_at` plus `eaten_at_timezone`. Do not include an offset on `local_eaten_at`.
Do not include meal-level `name`, item-level `quantity`, nested `macros`, or nested `nutrients`; these are rejected. Put portion details in `portion_description` or encode them in the item `name`.

`meals update` recalculates totals from items when item values are present. A healthy response includes:

```json
"nutrition_integrity": {
  "item_total_mismatch": false,
  "total_calories_source": "item_sum"
}
```

## Target JSON

Use flat numeric keys for target maps. Examples include:

```json
{
  "calories": 2400,
  "protein_g": 165,
  "carbs_g": 260,
  "fat_g": 75,
  "steps": 9000
}
```

For weekday target schedules, weekday keys must be lowercase English day names:

```json
{
  "monday": {
    "calories": 2600,
    "protein_g": 170
  },
  "sunday": {
    "calories": 2200,
    "protein_g": 165
  }
}
```

## Common Pitfalls

- Meal timestamps are optional on save; omit them for just-now meals.
- For specified local meal times, use `local_eaten_at` without an offset and `eaten_at_timezone`; for absolute `eaten_at`, include an offset such as `2026-05-31T12:00:00+08:00` or `Z`.
- Workout range datetimes and health sample datetimes must include an offset.
- Use `--start` and `--end`, not `--start-date` or `--end-date`.
- Use lowercase weekday keys such as `"monday"`, not `"1"` or `"Mon"`.
- Use `calories` at item level and `total_calories` at meal level.
- Use confidence as a float such as `0.6`, not a label such as `"medium"`.
- All timestamps are stored in UTC remotely; adjust for the user's local timezone when reading.
- Always pass `--json` when parsing command output.

## Known Limitations

- No bulk deactivate for projections; loop through projection IDs when needed.
- `targets schedule show` returns a `{"projection": {...}}` wrapper.
- There is no `targets daily list` subcommand; use `projections list` or target schedule reads depending on the question.
