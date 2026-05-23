---
name: fitness-program-design
description: Design and maintain fitness programs with the AI Fitness CLI. Use when a user asks for a training plan, workout schedule, macro targets, phase targets, hybrid strength/cardio programming, injury-aware replanning, or a review of meals against active targets.
---

# Fitness Program Design

Use this skill for program design, target setting, phase planning, and injury-aware adjustments for users who have the `fitness` CLI installed and configured.

## Ground Rules

- Use the CLI as the primary source of truth. Run `fitness doctor` if setup is uncertain.
- Do not infer current health, workout, nutrition, or target data from memory when the CLI can read it.
- Ask for missing human constraints before locking a plan: age, height, weight, body fat estimate, equipment, training days, session duration, schedule limits, injuries, goal, timeline, cardio preferences, and dietary restrictions.
- Explain data gaps briefly. Distinguish reliable device data from stale, missing, or user-estimated values.
- Verify all writes by reading the relevant data back.

## Initial Data Pull

Run the narrowest set of commands needed for the request. For a full programme design, use:

```bash
fitness doctor
fitness sync status --json
fitness health catalog --json
fitness context brief --json
fitness health summary --start YYYY-MM-DD --end YYYY-MM-DD --json
fitness workouts list --start YYYY-MM-DDT00:00:00+00:00 --end YYYY-MM-DDT23:59:59+00:00 --json
fitness meals summary --start YYYY-MM-DD --end YYYY-MM-DD --json
fitness health body --json
fitness profile show --json
fitness targets explain --as-of YYYY-MM-DD --json
```

Use the user's timezone when choosing dates and timestamps.

## Assess The Data

Summarize:

- Strong data: recent workouts, steps, heart rate, sleep, VO2 max, body metrics, or consistent meal logs.
- Missing or stale data: body composition, dietary macros, workout heart rate, profile demographics, injuries, or old nutrition imports.
- Planning implications: what can be calculated confidently and what needs user confirmation.

## Profile And Zones

If profile fields are missing or stale, ask the user for confirmation, then update:

```bash
fitness profile update --profile-file /tmp/profile.json --json
```

Useful profile fields include demographics, body metrics, heart-rate baselines/zones, injuries, mobility notes, training preferences, equipment, programme duration, and preferred cardio.

If max heart rate is unknown, use a standard estimate such as `220 - age` only as a temporary value. Prefer measured or user-provided max heart rate when available.

## Targets

Calculate from measured data first:

- BMR: use recent basal energy if available.
- Active burn: use recent active energy and workout history.
- TDEE: basal plus active energy, adjusted for observed trend and goal.
- Lean gain: small surplus, usually +200 to +400 kcal on strength days.
- Fat loss: moderate deficit, usually -300 to -500 kcal.
- Recomposition: near maintenance with high protein and progressive training.

Set macros in this order:

1. Protein: usually 1.6-2.2 g/kg bodyweight depending on goal, training, and injury context.
2. Fat: usually 0.6-1.0 g/kg bodyweight, higher if needed for preference or satiety.
3. Carbs: fill remaining calories and bias higher on harder training days.

Give expected weekly weight change and schedule a check-in after enough data accumulates, usually 1-2 weeks.

## Weekly Split Design

Build around the user's constraints and recovery:

- Separate heavy lower body sessions and high-intensity cardio by at least one day when practical.
- Put the hardest conditioning or lifting session where the user is most likely to be fresh.
- Back-to-back lifting days are fine if stress differs by muscle group or intensity.
- Keep at least one real recovery day in most plans.
- Adjust cardio modes around injuries, equipment, and user preference.

Example hybrid structure:

```text
Mon: Rest or mobility
Tue: Tempo or intervals
Wed: Lower strength
Thu: Zone 2 cardio
Fri: Cross-train or easy cardio
Sat: Upper strength
Sun: Full body moderate
```

## Save Programmes And Targets

Use the CLI's programme and target commands. Prefer JSON files for structured payloads:

```bash
fitness programme save --name "..." --start YYYY-MM-DD --end YYYY-MM-DD --goal "..." --payload-file /tmp/programme.json --json
fitness targets phase save --phase-name "..." --start YYYY-MM-DD --end YYYY-MM-DD --targets-file /tmp/targets.json --rationale "..." --json
fitness targets schedule save --start YYYY-MM-DD --end YYYY-MM-DD --default-targets-file /tmp/default-targets.json --json
fitness targets explain --as-of YYYY-MM-DD --json
```

Target layers:

- Phase targets: baseline daily values for the date range.
- Weekly overrides: repeating day-of-week values for training/rest patterns, if supported by the active backend.
- Daily adjustments: one-off date-specific changes for exceptions.

After saving, re-read targets and confirm normalized daily values match the intended plan.

## Review Meals Against Plan

When asked to review meals or a day of eating:

```bash
fitness targets explain --as-of YYYY-MM-DD --json
fitness meals summary --start YYYY-MM-DD --end YYYY-MM-DD --json
fitness meals list --start YYYY-MM-DD --end YYYY-MM-DD --json
```

Compare calories, protein, carbs, and fat against the active target. Call out the specific foods driving any overage or shortfall, then suggest concrete swaps.

## Injury-Aware Redesign

When a new injury changes training capacity:

1. Pull current context, targets, workouts, and recent activity.
2. Compare pre-injury and post-injury activity using actual device data where available.
3. Avoid assuming TDEE collapses just because training stops; crutches, altered gait, inflammation, and healing can keep expenditure higher than expected.
4. Do not default to a large surplus. Use measured maintenance unless appetite, weight trend, or clinical guidance supports otherwise.
5. Keep protein adequate, usually around normal high-protein targets; extra protein does not fully overcome immobilization-related anabolic resistance.
6. Create a clear recovery phase, extend the timeline if needed, and verify the active targets after saving.

If the user challenges conventional recovery advice, search current evidence from reliable medical or sports-nutrition sources before committing.

## Common Pitfalls

- Do not save targets without at least one numeric baseline target.
- Do not assume stale HealthKit nutrition macros represent the user's current diet.
- Do not treat missing catalog metrics as merely delayed; they may not be tracked or ingested.
- Do not rely on API/CLI success alone. Always read back persisted programmes, projections, or targets.
- Do not lock a generic template before asking about schedule, equipment, injuries, sleep, and preferences.
