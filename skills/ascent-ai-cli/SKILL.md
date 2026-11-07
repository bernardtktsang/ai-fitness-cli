---
name: ascent-ai-cli
description: Use when working with the Ascent AI CLI `fitness`, including setup, login, remote API connectivity, command reference, meal logging, meal updates, workouts, health data, targets, programmes, projections, dashboard metrics, JSON schemas, and common validation pitfalls.
---

# Ascent AI CLI

Use this skill as the command and schema reference for the remote-only Ascent AI CLI.

## Default Workflow

1. Run `fitness doctor` when setup, auth, API URL, or credential state is uncertain.
2. Use `--json` for commands whose output will be parsed programmatically.
3. For structured writes, create a temporary JSON file and pass it with the relevant `--file` or `--*-file` flag.
4. For meals being logged right now, omit `eaten_at` and let the backend stamp the save time. For past/specific local meal times, use local `eaten_at` plus `timezone`; offset-only datetimes are accepted, but do not combine offsets with `timezone`.
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
fitness context trend --weeks 4 --json
fitness targets explain --as-of YYYY-MM-DD --json
```

Meals:

```bash
fitness meals summary --start YYYY-MM-DD --end YYYY-MM-DD --json
fitness meals list --start YYYY-MM-DD --end YYYY-MM-DD --json
fitness meals save --file /tmp/meal.json --json
fitness meals update --meal-id <uuid> --file /tmp/meal.json --json
fitness meals delete --meal-id <uuid> --json
fitness meals add --title "Protein shake" --calories 250 --protein 30 --json
fitness meals scale --meal-id <uuid> --servings-scale 1.5 --json
fitness meals item-update --meal-id <uuid> --item-id <uuid> --item-update-json '{"servings_scale": 0.5, "calories": 300}' --json
fitness meals item-delete --meal-id <uuid> --item-id <uuid> --json
fitness meals undo --meal-id <uuid> --json
```

Always give `meals save` a short `title` (max 80 chars, e.g. `Chicken rice bowl`); the app shows it on the meal card and `meal_type` is no longer shown. If omitted the backend derives one from the items. `meals scale`/`item-update`/`item-delete` recompute totals and note the edit in `correction_notes`; `meals undo` only works for about 60 seconds after creation (otherwise use `meals delete`).

The generated long-form file flags are also valid: `--meal-file` for `meals save` and `--meal-update-file` for `meals update`.

Food history:

```bash
fitness foods search "rice" --json
fitness foods get "soba noodles" --json
fitness foods history "chicken breast" --json
fitness foods list --limit 50 --json
```

Use `fitness foods search` or `fitness foods get --json` before re-estimating
common foods when time permits. Food history returns prior logged entries from
this user's meal history; it is not a generic food database and does not provide
per-100g averages.

Structured nutrition lookup:

```bash
fitness nutrition lookup "char siu rice" --portion-hint "one plate" --json
```

Health and workouts:

```bash
fitness health summary --start YYYY-MM-DD --end YYYY-MM-DD --json
fitness health body --json
fitness health catalog --json
fitness workouts list --start DATETIME --end DATETIME --json
fitness workouts save --file /tmp/workout.json --json
fitness workouts update --workout-id <uuid> --file /tmp/workout-update.json --json
fitness workouts delete --workout-id <uuid> --json
fitness sync status --json
```

Strength logbook (routines, exercise library, sessions, PRs; weights are kg):

```bash
fitness routines list --json
fitness routines save --file /tmp/push.json --json
fitness routines get --routine-id <uuid> --json
fitness routines delete --routine-id <uuid> --json
fitness exercises search --q bench --muscle chest --json
fitness exercises search --scope suggested --routine-id <uuid> --json
fitness exercises create --file /tmp/exercise.json --json
fitness exercises history --exercise barbell-bench-press --metric e1rm --range 3M --json
fitness exercises prs --exercise barbell-bench-press --json
fitness sessions list --start YYYY-MM-DD --end YYYY-MM-DD --json
fitness sessions get --session-id <uuid> --json
fitness sessions save --file /tmp/session.json --timezone Asia/Hong_Kong --json
```

To build a split (Push/Pull/Legs), search for exercises, then call
`routines save` once per routine. Reference exercises by `slug` (from
`exercises search`) or exact name; exercise order is workout order:

```json
{"name": "Push", "exercises": [
  {"exercise": "barbell-bench-press", "target_sets": 3, "target_reps": 8, "target_kg": 60},
  {"exercise": "overhead-press", "target_sets": 3, "target_reps": 10}
]}
```

Pass `routine_id` inside the JSON to replace an existing routine. `sessions save`
only backfills a *finished* session the user already did (the app starts and
finishes live sessions); `finished_at` is required, sets count as completed
unless `"completed": false`, warm-ups use `"is_warmup": true`. Exercise types:
weighted (kg, reps), bodyweight (reps, optional added kg), assisted (assistance
in `kg`, lower is better), timed (`duration_seconds`). PRs ignore warm-ups, and
the first session of an exercise is a baseline. Metrics for `exercises history`:
weighted `heaviest|e1rm|volume`, bodyweight `reps|added_kg`, assisted
`assistance`, timed `hold`.

Before manually saving a workout, list the relevant time range and avoid
duplicating a workout already synced from HealthKit. Use manual writes only for
missing records or when the user explicitly asks to correct one.

Goals (text records the user sees on their Profile; no numbers, targets hold numbers):

```bash
fitness goals list --json
fitness goals list --include-archived --json
fitness goals save --title "Run a 10k" --description "Why and by when" --json
fitness goals save --id <uuid> --title "..." --description "..." --json
fitness goals archive --id <uuid> --json
```

Goals are recorded as written by Ascent. Do not rewrite a goal the user wrote
unless they asked. Max 20 active goals; archive one before adding another.
Update an existing goal with `--id` instead of creating a duplicate.

Targets and programmes:

```bash
fitness targets validate --targets-file /tmp/t.json
fitness targets phase save --phase-name "Name" --start YYYY-MM-DD --end YYYY-MM-DD --targets-file /tmp/t.json --json
fitness targets schedule save --start YYYY-MM-DD --end YYYY-MM-DD --default-targets-file /tmp/d.json --weekday-targets-file /tmp/w.json --json
fitness targets schedule list --json
fitness targets schedule show --projection-id <uuid> --json
fitness targets schedule update --projection-id <uuid> --weekday-targets-file /tmp/w.json --json
fitness targets daily save --date YYYY-MM-DD --targets-file /tmp/d.json --json
fitness programme list --json
fitness programme save --name "Name" --start YYYY-MM-DD --end YYYY-MM-DD --goal "..." --payload-file /tmp/p.json --json
fitness programme activate --projection-id <uuid> --json
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
fitness dashboard metrics show --json
fitness dashboard metrics set --today calories,protein_g,steps --week calories,protein_g,steps --json
fitness dashboard metrics set --primary-today deficit_kcal --today deficit_kcal,calories,protein_g --week deficit_kcal,workouts --json
```

When an agent sets numeric nutrition, activity, recovery, or target metrics, it should
normally include at least those same target metric keys in the dashboard Today
and/or Week metric lists so the user can see progress against the targets in the
iOS app. Add extra context metrics when useful, but do not hide newly managed
targets from dashboard rendering unless the user explicitly wants a leaner view.

`--primary-today` picks the metric emphasized as the large Today hero card; it must
also appear in `--today` (the iOS app renders it only as the hero, not as a duplicate
row). Pass `--primary-today none` to clear the emphasis. The user can also edit these
same preferences by hand in the iOS app, so run `fitness dashboard metrics show
--json` before overwriting.

Config and bundled skills:

```bash
fitness config show --json
fitness skills list --json
fitness skills show ascent-ai-cli
fitness skills export --dest /path/to/skills
```

## Meal JSON

Use only the backend's accepted flat keys. Do not send nested `macros`, `nutrients`, `nutrition`, or similar objects.

Example:

```json
{
  "eaten_at": "2026-05-31T12:00:00",
  "timezone": "Asia/Hong_Kong",
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
  "notes": "estimated from user description",
  "source": "agent"
}
```

Item-level fields:

- `name` (string, required)
- `calories` (number, required)
- `protein_g` (number, required)
- `carbs_g` (number, required)
- `fat_g` (number, required)
- `fiber_g` (number)
- `sugar_g` (number)
- `sodium_mg` (number)
- `saturated_fat_g` (number)
- `caffeine_mg` (number)
- `water_ml` (number)
- `portion_description` (string)
- `confidence` (float from 0.0 to 1.0)

Meal-level fields:

- `eaten_at` (ISO 8601 datetime, optional local meal time when paired with `timezone`; offset-only absolute timestamp when `timezone` is omitted)
- `timezone` (IANA timezone such as `Asia/Hong_Kong`, used to interpret naive `eaten_at`)
- `meal_type` (`breakfast`, `lunch`, `dinner`, or `snack`)
- `items` (array, required)
- `notes` (string)
- `source` (string)

- If the meal is being logged right now, omit `eaten_at`; the backend records the save time.
- If the user specifies a local time, prefer `eaten_at` plus `timezone`. Do not include an offset when `timezone` is present.
Do not include meal-level `name`, meal-level nutrition fields such as `total_calories`/`protein_g`, item-level `quantity`, nested `macros`, or nested `nutrients`; these are rejected. Put portion details in `portion_description` or encode them in the item `name`.

When `items` is supplied to `meals update`, it must be a full replacement with complete item nutrition. A healthy response includes:

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
  "steps": 9000,
  "sleep_duration": 8
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
- For specified local meal times, use `eaten_at` without an offset plus `timezone`; for absolute `eaten_at`, include an offset such as `2026-05-31T12:00:00+08:00` or `Z` and omit `timezone`.
- Workout and health range datetimes may be date-only, naive local datetimes, or offset-only absolute datetimes; do not combine offsets with `--timezone`.
- Use `--start` and `--end`, not `--start-date` or `--end-date`.
- Use lowercase weekday keys such as `"monday"`, not `"1"` or `"Mon"`.
- Use `calories` at item level and `total_calories` at meal level.
- Use confidence as a float such as `0.6`, not a label such as `"medium"`.
- Agent-facing output already uses local datetime fields plus `timezone`; do not reinterpret them as UTC.
- Always pass `--json` when parsing command output.

## Known Limitations

- No bulk deactivate for projections; loop through projection IDs when needed.
- `targets schedule show` returns a `{"projection": {...}}` wrapper.
- There is no `targets daily list` subcommand; use `projections list` or target schedule reads depending on the question.
