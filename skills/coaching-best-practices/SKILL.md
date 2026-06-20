---
name: coaching-best-practices
description: Use when coaching a user for motivation and adherence — summarize progress and encourage when they are on track, propose habit stacking at plan setup ("tie the workout to dinner"), and ask the user to choose their own reward. Applies Atomic Habits "make it attractive" (habit stacking) and "make it satisfying" (self-chosen reward).
---

# Coaching Best Practices

Use this skill to coach adherence through the `fitness` CLI. It layers two Atomic
Habits ideas on top of the program-design and meal-logging workflows: **make it
attractive** (habit stacking) and **make it satisfying** (a self-chosen reward
plus honest, encouraging progress feedback). It adds no new commands; it reuses
the existing allowlisted `fitness` commands.

## When To Use

- You are giving a check-in or status update to a user following a programme.
- You are setting up or revising a programme with the user (see `fitness-program-design`).
- The user is discouraged, or has just hit or missed a target, streak, or milestone.

## Summarize Progress And Encourage When On Track

Read the agent context brief; do not recompute a separate progress summary. The
brief already carries the goal, current phase, and per-target `met`/`near`/`off`
status with a short narrative line:

```bash
fitness context brief --json
```

For deeper plan math when the user asks, use:

```bash
fitness progress show --json
fitness targets explain --as-of YYYY-MM-DD --json
```

Then:

- When the brief shows the user **on track** (targets `met` or `near`), lead with
  short, specific encouragement that names what they did well — the protein
  streak, the weekly deficit — instead of generic praise.
- Keep it to one or two sentences in chat. Cite the brief's own numbers; do not
  invent figures and do not author a second progress calculation here.
- When a status is `off`, stay supportive and concrete: name the one target to
  refocus on, not a list, and pair the nudge with what is still going well.
- If the encouragement is durable and worth seeing in the iOS app (a weekly win
  or a milestone), persist it as a dashboard note; skip this for ordinary chat
  replies:

```bash
fitness recommendation write --title "Nice week" --message "..." --priority normal --json
```

## Propose Habit Stacking At Plan Setup

When setting up or revising a programme, make a new behavior **attractive** by
stacking it onto an existing daily anchor the user already does reliably. The
formula is "after/before [existing habit], I will [new habit]":

- "Tie the workout to dinner" — train right before dinner so dinner is the cue.
- "After morning coffee, log yesterday's weight."
- "Before the evening shower, do the mobility set."

Ask the user which existing anchors are most reliable, propose one stack per new
habit, and confirm the pairing. Record the agreed habit stack as unstructured
coaching context in your agent memory — it is a preference/habit, not structured
backend data, so do not invent a backend field for it. Surface it back when you
next check in.

## Ask The User Their Self-Chosen Reward

Make the habit **satisfying** by having the user pick their own reward, not one
you assign:

- At plan setup, and when a phase or streak milestone is reached, ask: "What
  reward do you want to give yourself when you hit this?"
- Let the user choose it; a self-chosen reward sticks better than an imposed one.
- Prefer rewards that do not undo the goal — avoid a binge as the reward for a
  deficit week.
- Record the chosen reward in your agent memory alongside the milestone it is
  tied to, and bring it up when they earn it so the loop closes.

## Stay Consistent

- Reuse existing commands only; this skill adds no new CLI or tool surface.
- The progress read is the brief from `fitness context brief`; do not maintain a
  parallel progress summary here.
- Reward and habit-stack choices are unstructured coaching context for agent
  memory, not Postgres writes. Structured fitness data still goes through the CLI.
