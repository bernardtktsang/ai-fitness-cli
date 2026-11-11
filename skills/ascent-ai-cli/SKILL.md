---
name: ascent-ai-cli
description: Use when working with the Ascent AI CLI `fitness`, including setup, login, remote API connectivity, command reference, meal logging, meal edits, strength routines with per-set targets, sessions, recently deleted and restore, readiness, workouts, health data, targets, programmes, dashboard metrics, week start, JSON schemas, and common validation pitfalls.
---

# Ascent AI CLI

Use this skill as the command and schema reference for the remote-only Ascent AI CLI.

The CLI exposes the same operations (tool surface v2.1) as the in-app coach chat and the MCP
connector, so every command below is one of those operations: reads are coarse, writes are
small and explicit, and deletes are soft deletes you can undo.

## Default Workflow

1. Run `fitness doctor` when setup, auth, API URL, or credential state is uncertain. It also checks that the server speaks the v2.1 command surface (`tool_surface=v2.1`).
2. Start with `fitness context brief --json`, then use the narrow reads (`context day`, `sessions list`, `routines list`, `health trends`, `foods search`) for detail.
3. Use `--json` for commands whose output will be parsed programmatically.
4. For structured writes, create a temporary JSON file and pass it with the relevant `--file` or `--*-file` flag (or inline with `--*-json`).
5. For meals being logged right now, omit `eaten_at` and let the backend stamp the save time. For past/specific local meal times, use local `eaten_at` plus `timezone`; offset-only datetimes are accepted, but do not combine offsets with `timezone`. Future times are rejected.
6. After remote writes, read back the relevant resource when correctness matters.

Deletes (`meals delete`, `sessions delete`, `routines delete`, `workouts delete`) are soft deletes: the item moves to Recently deleted for 30 days and `fitness deleted restore` brings it back. Still delete only what the user asked to remove, and edit (never delete) to fix data.

Only impossible input is rejected: blank names, future dates for logged items, negative numbers, kg on a timed exercise or seconds on a weighted one, unknown metric names. The server's error says how to fix the call; read it and retry. Outliers are never flagged.

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

Expected setup output includes `mode=remote`, `api_url`, credential details and `tool_surface=v2.1`. If credentials are missing, run:

```bash
fitness login
```

If commands fail while referencing old local paths, reinstall with `--force`.

## Quick Reference

Daily status and reads:

```bash
fitness context brief --json                       # today + week vs targets, effective targets and their source
fitness context brief --include goals,programmes,profile,dashboard,sync,metrics,memory --json
fitness context day --date YYYY-MM-DD --json      # meals, nutrition, Apple Health, workouts, strength sessions
fitness context trend --weeks 4 --json
fitness targets show --as-of YYYY-MM-DD --json     # same brief: effective targets and user_set_targets
fitness sync status --json
fitness health trends --start YYYY-MM-DD --end YYYY-MM-DD --sections health,body,nutrition,trend,workouts,samples --json
fitness health summary --start YYYY-MM-DD --end YYYY-MM-DD --json
fitness health body --metrics weight_kg,body_fat_percent --json
```

`health trends --sections samples` needs `--sample-metrics`. Dates are ISO dates.

Meals:

```bash
fitness meals list --date YYYY-MM-DD --json
fitness meals summary --start YYYY-MM-DD --end YYYY-MM-DD --json
fitness meals save --file /tmp/meal.json --json
fitness meals update --meal-id <uuid> --file /tmp/meal.json --json
fitness meals add --title "Protein shake" --calories 250 --protein 30 --json
fitness meals scale --meal-id <uuid> --servings-scale 1.5 --json
fitness meals item-update --meal-id <uuid> --item-id <uuid> --item-changes-json '{"servings_scale": 0.5, "calories": 300}' --json
fitness meals item-delete --meal-id <uuid> --item-id <uuid> --json
fitness meals delete --meal-id <uuid> --json
```

Always give `meals save` a short `title` (max 80 chars, e.g. `Chicken rice bowl`); the app shows it on the meal card. If omitted the backend derives one from the items. `meals scale`/`item-update`/`item-delete` recompute totals and note the edit in `correction_notes`. A mistaken save is fixed with `meals delete` (then `deleted restore` if it was wrong to delete). Each meal edit takes exactly one change mode.

The long-form file flags are `--meal-file` for `meals save` and `--meal-update-file` for `meals update`.

Food history and lookup:

```bash
fitness foods search "rice" --json          # foods the user has logged, exact/whole foods first
fitness foods list --limit 50 --json        # their most frequently logged foods
fitness foods lookup "char siu rice" --portion-hint "one plate" --json   # nutrition databases
```

Use `fitness foods search` before re-estimating common foods when time permits. Food
history returns prior logged entries from this user's meal history; it is not a generic
food database and does not provide per-100g averages. Use `foods lookup` for unfamiliar,
branded, packaged or restaurant foods.

Workouts (runs, rides, swims; strength training is a session, below):

```bash
fitness workouts list --start YYYY-MM-DD --end YYYY-MM-DD --json
fitness workouts save --file /tmp/workout.json --json
fitness workouts update --workout-id <uuid> --changes-file /tmp/workout-update.json --json
fitness workouts delete --workout-id <uuid> --json
```

Before manually saving a workout, list the relevant range and avoid duplicating a workout
already synced from HealthKit. Use manual writes only for missing records or when the user
explicitly asks to correct one.

Strength routines (per-set targets; weights are kg):

```bash
fitness routines list --json
fitness routines list --readiness --json            # muscle readiness per routine + the up-next pick
fitness routines get --routine <id|slug|name> --json   # --routine-id is the same flag; id, slug or exact name
fitness routines save --routines-file /tmp/programme.json --json   # several routines, all-or-nothing; each upserted by name
fitness routines save --file /tmp/push.json --json   # one routine; upsert by name: replaces the routine with that name
fitness routines save --name Push --exercise "barbell-bench-press:3x8-10@60" --exercise "plank:3x45s" --json
fitness routines edit --routine-id <uuid> --ops-file /tmp/ops.json --json
fitness routines days --routine <id|slug|name> --days mon,thu --json   # planned weekdays (mon..sun); --days '' clears
fitness routines pin --routine-id <uuid> --json      # pin as today's up-next pick
fitness routines move --routine-id <uuid> --position 0 --json
fitness routines delete --routine-id <uuid> --json
fitness suggest-next --routine <id|slug|name> --json   # next kg/reps (seconds) per exercise, with the reason and a stalled flag
```

`routines save` creates or replaces by name (names are unique, case-insensitive); send the
full exercise list in workout order. `--routines-file` takes a JSON list of routines (or
`{"routines": [...]}`) and saves them all or none, so save a whole programme in one call.
Each routine may carry `days` (planned weekdays `mon`..`sun`; omit to leave unchanged, `[]`
clears) and `position`. The single-routine flags (`--file`, `--name/--exercise`, `--position`,
`--days`) build a one-item list. Reference exercises by `slug` (from `exercises search`)
or exact name. Give per-set targets as a `sets` list, or use the single-target shortcut:

```json
{"name": "Push", "exercises": [
  {"exercise": "barbell-bench-press", "rest_seconds": 150, "sets": [
    {"set_type": "warmup", "kg": 40, "reps": 10},
    {"kg": 60, "reps": "6-8"},
    {"kg": 60, "reps": "6-8"},
    {"set_type": "drop", "kg": 45, "reps": "8-12"}
  ]},
  {"exercise": "overhead-press", "sets": 3, "reps": "8-10", "kg": 12.5},
  {"exercise": "plank", "sets": 3, "seconds": 45}
]}
```

Set types are `warmup`, `working`, `drop`, `failure`. The shortcut `sets: 3, reps: "8-10",
kg: 12.5` expands to three working sets; the CLI flag form is `<exercise>:<sets>x<reps>[@<kg>]`
(timed: `plank:3x45s`). A timed exercise takes `seconds`, never `kg`; a weighted one takes `kg`
and `reps`, never `seconds`.

For small changes use `routines edit` with ops applied atomically, e.g.:

```json
[{"op": "rename", "name": "Push A"},
 {"op": "add_exercise", "exercise": "triceps-pushdown", "sets": 3, "reps": "10-12", "at": 2},
 {"op": "replace_sets", "exercise": "barbell-bench-press", "sets": [{"kg": 62.5, "reps": "5-6"}]},
 {"op": "set_rest", "exercise": "barbell-bench-press", "rest_seconds": 180},
 {"op": "move_exercise", "exercise": "plank", "to": 0},
 {"op": "remove_exercise", "exercise": "overhead-press"}]
```

Add `{"op": "set_days", "days": ["mon", "thu"]}` to change planned weekdays (or use `routines days`).
`routines edit` also takes `--pin-up-next` and `--position`. A rename to a name another routine
already has is rejected with the server's message.

Exercise library, progress and PRs:

```bash
fitness exercises search --q bench --muscle chest --json
fitness exercises search --scope suggested --routine <id|slug|name> --json
fitness exercises create --file /tmp/exercise.json --json
fitness exercises rename --exercise <slug-or-id> --name "Low Cable Fly" --json
fitness exercises archive --exercise <slug-or-id> --json      # custom exercises only; also: unarchive
fitness exercises progress --exercise barbell-bench-press --metric e1rm --range 3M --json   # series + personal records; range 1M, 3M, 1Y or ALL
```

Metrics for `exercises progress`: weighted `heaviest|e1rm|volume`, bodyweight `reps|added_kg`,
assisted `assistance`, timed `hold`. Exercise types: weighted (kg, reps), bodyweight (reps,
optional added kg), assisted (assistance in `kg`, lower is better), timed (`duration_seconds`).
PRs ignore warm-ups, and the first session of an exercise is a baseline.

Strength sessions:

```bash
fitness sessions list --start YYYY-MM-DD --end YYYY-MM-DD --json
fitness sessions get --session-id <uuid> --json
fitness sessions save --file /tmp/session.json --timezone Asia/Hong_Kong --json
fitness sessions edit --session-id <uuid> --name "Chest" --notes "felt good" --json
fitness sessions edit --session-id <uuid> --exercises-file /tmp/exercises.json --json   # replaces exercises and sets
fitness sessions sync-routine --session-id <uuid> --dry-run --json   # preview the diff against the source routine
fitness sessions sync-routine --session-id <uuid> --json              # write the session back to its source routine
fitness sessions sync-routine --session-id <uuid> --new-routine-name "Chest A" --json   # save it as a new routine
fitness sessions delete --session-id <uuid> --json
```

`sessions save` only backfills a *finished* session the user already did (the app starts and
finishes live sessions); `finished_at` is required and future times are rejected. Sets count
as completed unless `"completed": false`; mark `"set_type"` as `warmup`, `working`, `drop` or
`failure`. Run `sync-routine --dry-run` before applying so the user can confirm the routine change.

Suggest-next, memory and duplicate protection:

```bash
fitness suggest-next --routine "Push A" --json    # double progression; read-only, then write the numbers with routines edit
fitness memory list --json                       # saved durable notes with created/updated times
```

`suggest-next` adds weight (+2.5 kg upper body, +5 kg lower) when every working set hit the top
of its rep range, otherwise +1 rep (bodyweight +1 rep, timed +5 s), and flags `stalled` after 3
sessions without progress; warm-ups never count.

Routines, sessions, meals, exercises and goals in responses carry `created_at`, `updated_at` and
an integer `revision`. Identical write commands within 10 minutes are not applied twice: the
response says `duplicate of <id>` (JSON: a top-level `duplicate_of`) and returns the existing
record, so a retry after a timeout is safe. If you see `duplicate_of`, do not repeat the write.
Wherever a command takes a routine or exercise, pass an id, a slug or the exact name.

Recently deleted (kept 30 days):

```bash
fitness deleted list --json                       # who deleted it (user, coach, agent) and days left
fitness deleted list --type meals --json          # all | workouts | meals | routines
fitness deleted restore --type session --id <uuid> --json   # type: meal | session | routine | workout
```

A restored routine whose name is now taken gets a ` (2)` suffix.

Goals (text records the user sees on their Profile; no numbers, targets hold numbers):

```bash
fitness goals list --json
fitness goals save --title "Run a 10k" --description "Why and by when" --json
fitness goals save --id <uuid> --title "..." --description "..." --json
fitness goals archive --id <uuid> --json
```

Goals are recorded as written by Ascent. Do not rewrite a goal the user wrote unless they
asked. Max 20 active goals; archive one before adding another. Update an existing goal with
`--id` instead of creating a duplicate.

Targets and programmes:

```bash
fitness targets phase save --phase-name "Name" --start YYYY-MM-DD --end YYYY-MM-DD --targets-file /tmp/t.json --json
fitness targets schedule save --start YYYY-MM-DD --end YYYY-MM-DD --default-targets-file /tmp/d.json --weekday-targets-file /tmp/w.json --json
fitness targets schedule save --projection-id <uuid> --weekday-targets-file /tmp/w.json --json   # update that schedule
fitness targets daily save --date YYYY-MM-DD --targets-file /tmp/d.json --json
fitness targets deactivate --projection-id <uuid> --json   # retire a phase, schedule or programme (reversible)
fitness programme list --json
fitness programme save --name "Name" --start YYYY-MM-DD --end YYYY-MM-DD --goal "..." --payload-file /tmp/p.json --json
fitness programme activate --projection-id <uuid> --json
```

User-set targets: the user can override any daily target in the Ascent app. Target
writes (`targets daily save`, `targets schedule save`, `targets phase save`) never change
a user-set key. The response lists them under `skipped_user_set` with a `hint`, and
`fitness targets show` lists them as `user_set_targets`. Do not retry or work around
the skip: suggest the change to the user in chat and let them update it in the app.
There is no CLI command to set or reset a user override; that is the user's call.

Profile, week start and dashboard:

```bash
fitness profile show --json
fitness profile update --profile-file /tmp/profile.json --json
fitness profile week-start sun --json               # mon | sun | sat
fitness dashboard metrics show --json
fitness dashboard metrics set --today calories,protein_g,steps --week calories,protein_g,steps --json
fitness dashboard metrics set --primary-today deficit_kcal --today deficit_kcal,calories,protein_g --week deficit_kcal,workouts --json
```

The week start day (`mon`, `sun` or `sat`) decides where the Week view and weekly progress
begin; change it only when the user asks. When an agent sets numeric nutrition, activity,
recovery, or target metrics, it should normally include at least those same target metric
keys in the dashboard Today and/or Week metric lists so the user can see progress against
the targets in the iOS app. Add extra context metrics when useful, but do not hide newly
managed targets from dashboard rendering unless the user explicitly wants a leaner view.

`--primary-today` picks the metric emphasized as the large Today hero card; it must also
appear in `--today`. Pass `--primary-today none` to clear the emphasis. The user can also
edit these same preferences by hand in the iOS app, so run `fitness dashboard metrics show
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
- Range reads (`health trends`, `workouts list`, `sessions list`, `meals summary`) take ISO dates via `--start` and `--end`, not `--start-date`/`--end-date`; day reads take `--date`.
- Use lowercase weekday keys such as `"monday"`, not `"1"` or `"Mon"`.
- Use `calories` at item level and `total_calories` at meal level.
- Use confidence as a float such as `0.6`, not a label such as `"medium"`.
- Agent-facing output already uses local datetime fields plus `timezone`; do not reinterpret them as UTC.
- Always pass `--json` when parsing command output.

## Known Limitations

- A target write that returns `skipped_user_set` still succeeded for the other keys; the skipped keys keep the user's value.
- There is no hard delete of plan items: retire them with `targets deactivate` (reversible).
- Agents keep their own long-term memory; the CLI can only read the saved notes (`fitness memory list`), it has no memory write command.
