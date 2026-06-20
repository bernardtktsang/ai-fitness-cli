# BYO Agent Operator Guide

Last updated: 2026-06-20

This guide is for a user-owned AI agent that operates AI Fitness Buddy through
the remote `fitness` CLI. It focuses on the durable operating loop after the
CLI has already been installed and configured.

For command/schema details, use the bundled skills:

```bash
fitness skills show ai-fitness-buddy-cli
fitness skills show meal-logging
fitness skills show fitness-program-design
fitness skills show coaching-best-practices
```

## First-Time Setup

The human user should install the CLI, create an Agent API key in the iOS app,
and run `fitness login` themselves. Agents should not ask users to paste API
keys into chat.

After setup, verify access:

```bash
fitness doctor
fitness context brief
```

## Operating Model

```text
iPhone HealthKit sync
  -> hosted AI Fitness Buddy API/Postgres
  -> user-owned agent runs fitness CLI
  -> user talks to that agent in their preferred chat/runtime
```

The hosted backend is the structured source of truth for HealthKit samples,
workouts, body metrics, nutrition logs, targets, programmes, dashboard state,
sync runs, and entitlement state.

The user's agent memory is for unstructured context: preferences, habits,
injuries, schedule constraints, coaching style, and long-running conversation.
Do not use agent memory as the structured nutrition or HealthKit database.

## Safety Rules

- Do not ask the user to paste API keys, `.env` files, or token values into chat.
- Do not print agent keys, sync keys, Hermes tokens, or secret environment variables.
- Do not store meal photos as app data. Save structured nutrition logs only.
- Do not write raw SQL against the production database for user fitness writes.
- Do not invent HealthKit values, body metrics, workouts, or meal logs. Read them with the CLI.
- Do not auto-log a meal from a photo alone. Wait for an explicit logging request or confirmation.
- Confirm destructive writes unless the user explicitly requested them: `fitness meals delete`, `fitness projections delete`, and `fitness targets schedule delete`.
- After important writes, read back the affected resource before telling the user it is settled.
- Use `--json` when parsing output programmatically.

## Daily Agent Loop

Start by checking current state:

```bash
fitness doctor
fitness context brief --json
fitness sync status --json
fitness targets explain --json
fitness progress show --json
```

Use narrower reads for specific questions:

```bash
fitness health summary --start YYYY-MM-DD --end YYYY-MM-DD --json
fitness health body --json
fitness health catalog --json
fitness workouts list --start YYYY-MM-DDT00:00:00+08:00 --end YYYY-MM-DDT23:59:59+08:00 --json
fitness meals summary --start YYYY-MM-DD --end YYYY-MM-DD --json
fitness meals list --start YYYY-MM-DD --end YYYY-MM-DD --json
```

Use the user's timezone when choosing dates. Date-range commands usually use
`--start` and `--end`; do not use `--start-date` or `--end-date`.

## Meal Logging

Before estimating a common recurring food, check personal food history when
time permits:

```bash
fitness foods search "rice" --json
fitness foods get "greek yogurt" --json
fitness foods history "chicken breast" --json
```

Food history is this user's prior logged food history. It is not a generic food
database and does not provide authoritative per-100g nutrition.

For a meal being logged right now, omit all timestamp fields and let the backend
stamp the save time:

```json
{
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
  "notes": "estimated from photo; portions approximate",
  "source": "agent"
}
```

Save with:

```bash
fitness meals save --file /tmp/meal.json --json
```

For a past or specific local meal time, use `eaten_at` without an offset
plus `timezone`:

```json
{
  "eaten_at": "2026-06-05T13:10:00",
  "timezone": "Asia/Hong_Kong",
  "meal_type": "lunch",
  "items": [
    {
      "name": "Beef noodle soup",
      "portion_description": "1 bowl, most broth left",
      "calories": 760,
      "protein_g": 38,
      "carbs_g": 86,
      "fat_g": 28,
      "sodium_mg": 1800,
      "confidence": 0.65
    }
  ],
  "source": "agent"
}
```

Accepted item-level nutrition keys are flat numeric fields:

```text
calories
protein_g
carbs_g
fat_g
fiber_g
sugar_g
sodium_mg
saturated_fat_g
caffeine_mg
water_ml
confidence
```

Do not send nested `macros`, `nutrients`, `nutrition`, item `quantity`, or
meal-level nutrition totals. Use `portion_description` for portion details.

## Meal Corrections

Use the returned meal ID for follow-up corrections. For corrections, rebuild the
full updated meal payload and replace the meal:

```bash
fitness meals update --meal-id <meal_id> --file /tmp/meal.json --json
```

When the user says "actually only half", "add the sauce", or "I drank the
broth", update the same meal unless they clearly started a separate meal.

When updating `items`, include the full corrected item list with complete
nutrition. The backend recalculates meal-level aggregate totals from `items`.

If the user explicitly wants a meal removed:

```bash
fitness meals delete --meal-id <meal_id> --json
```

Read back the relevant day after correction:

```bash
fitness meals list --start YYYY-MM-DD --end YYYY-MM-DD --json
fitness meals summary --start YYYY-MM-DD --end YYYY-MM-DD --json
```

## Target And Programme Management

Pull current target context before writing:

```bash
fitness context brief --json
fitness targets explain --as-of YYYY-MM-DD --json
fitness progress show --json
```

Target maps are flat numeric JSON objects. Important keys include:

```text
calories
protein_g
carbs_g
fat_g
fiber_g
sugar_g
sodium_mg
saturated_fat_g
caffeine_mg
water_ml
steps
active_energy_kcal
total_energy_kcal
walking_running_distance_m
deficit_kcal
exercise_minutes
workouts
```

Energy target aliases such as `target_total_energy_kcal` and
`target_deficit_kcal` are normalized by the backend. If `calories` plus
`total_energy_kcal` are provided, the backend derives `deficit_kcal`. If
`calories` plus `deficit_kcal` are provided, it derives `total_energy_kcal`.

Validate target JSON before saving when possible:

```bash
fitness targets validate --targets-file /tmp/targets.json
```

Save the active programme:

```bash
fitness programme save \
  --name "Lean Strength Block" \
  --start YYYY-MM-DD \
  --end YYYY-MM-DD \
  --goal "Lean gain while preserving conditioning" \
  --payload-file /tmp/programme.json \
  --json
```

Save a phase-level daily target template:

```bash
fitness targets phase save \
  --phase-name "Base Building" \
  --start YYYY-MM-DD \
  --end YYYY-MM-DD \
  --targets-file /tmp/phase-targets.json \
  --weekly-overrides-file /tmp/weekly-overrides.json \
  --rationale "Base daily targets for the current training phase." \
  --json
```

Use `weekly_overrides` only for weekly totals that should not be multiplied by
7, such as:

```json
{
  "exercise_minutes": 350,
  "workouts": 5,
  "deficit_kcal": 2100
}
```

Save repeating day-type rules with a target schedule:

```bash
fitness targets schedule save \
  --start YYYY-MM-DD \
  --end YYYY-MM-DD \
  --default-targets-file /tmp/default-targets.json \
  --weekday-targets-file /tmp/weekday-targets.json \
  --json
```

Weekday keys should be lowercase English day names:

```json
{
  "monday": {
    "calories": 2600,
    "protein_g": 170,
    "total_energy_kcal": 2850
  },
  "sunday": {
    "calories": 2200,
    "protein_g": 165,
    "total_energy_kcal": 2500
  }
}
```

Save one-off daily overrides only for a specific date:

```bash
fitness targets daily save \
  --date YYYY-MM-DD \
  --targets-file /tmp/daily-targets.json \
  --rationale "Adjusted for travel day." \
  --json
```

After any target write, read back:

```bash
fitness targets explain --as-of YYYY-MM-DD --json
fitness progress show --json
```

## Dashboard Updates

Set which metrics the app shows in Today and Week:

```bash
fitness dashboard metrics set \
  --today deficit_kcal,calories,protein_g,steps \
  --week deficit_kcal,exercise_minutes,workouts,protein_g \
  --json
```

Write dashboard recommendations only when the message is useful as a persistent
dashboard note, not for every chat reply:

```bash
fitness recommendation write \
  --title "Today's focus" \
  --message "Keep the deficit moderate, hit protein, and move the interval session to tomorrow if the ankle is sore." \
  --priority normal \
  --recommendation-date YYYY-MM-DD \
  --json
```

Use dashboard recommendations for durable advice the user should see in the
iOS app: today's focus, an injury-aware adjustment, a target rationale, or a
weekly check-in summary.

Do not use dashboard recommendations for transient chat responses, raw command
output, secrets, or speculation.

## Export, Delete, And Support Expectations

For hosted beta users, agents should be able to explain these expectations:

- The backend stores structured HealthKit-derived samples, workouts, body metrics, nutrition logs, targets, programme state, dashboard state, sync history, user profile, entitlement state, and scoped API key metadata.
- Meal photos should not be stored as application data; the durable record is the structured nutrition log.
- Users should revoke agent keys they no longer use from the iOS app.
- Account export/delete should be handled through the hosted support path until self-serve account controls exist.
- Agents should not promise medical advice, diagnosis, treatment, or guaranteed fitness outcomes.

## Troubleshooting

If anything seems off:

```bash
fitness doctor --json
fitness config show --json
fitness sync status --json
fitness context brief --json
```

Common cases:

- `fitness doctor` says not logged in: ask the user to run `fitness login`; do not ask for the key in chat.
- Health data looks stale: check `fitness sync status --json` and ask the user to open the iOS app if background sync has not run recently.
- Meal save succeeded but daily summary looks stale: check `fitness meals list` before assuming the save failed.
- Validation fails on meal JSON: remove nested macro/nutrient objects, item `quantity`, and meal-level nutrition totals.
- Validation fails on targets: use flat numeric target maps and accepted metric keys.
- A destructive write is requested ambiguously: confirm which meal/projection/schedule to delete before running it.

## Minimal Agent Prompt

Use this as a seed instruction for a user-owned shell-capable agent:

```text
For fitness, health, nutrition, workout, dashboard, target, or progress
questions, use the `fitness` CLI. Run `fitness doctor` if setup is uncertain.
Use `fitness context brief --json` before personalized answers when current
state matters. Use `--json` when parsing output.

Never ask me to paste API keys or secrets into chat. If login is needed, ask me
to run `fitness login` myself. Do not print secret environment variables.

For meals, do not log from a photo unless I ask you to log it or confirm the
estimate. For meals I am logging right now, omit `eaten_at`. For past local
meal times, use local `eaten_at` and `timezone`.

For writes, use temporary JSON files and verify important changes by reading
them back. Confirm destructive deletes unless I explicitly asked for the exact
delete. Do not use raw SQL for user fitness writes.
```
