---
name: meal-logging
description: Log, update, and review meals with the AI Fitness CLI from food photos, text descriptions, voice corrections, or nutrition labels. Use when a user wants nutrition estimates saved, corrected, confirmed, or compared against daily targets.
---

# Meal Logging

Use this skill when the user wants to estimate, save, update, confirm, or review meal logs through the `fitness` CLI.

## Ground Rules

- Use the CLI for meal reads and writes. Run `fitness doctor` if setup is uncertain.
- Never auto-log a meal from a photo alone. A photo is not consent to save; ask or wait for an explicit logging request.
- Present estimated totals before saving unless the user has already clearly asked you to log the meal.
- Mark photo-based estimates as approximate and invite corrections.
- Do not ask for the meal time when the user says they just ate it; use the current message time with timezone offset. Ask only if they ate it earlier or for a different date.
- Use the user's timezone for `eaten_at`; include an offset such as `2026-05-23T13:10:00+08:00`.

## Analyze Input

Photo:

- Identify every visible item.
- Estimate portions using scale references such as fork, spoon, mug, hand, plate rim, or container size.
- Be conservative with styled overhead photos, which often make portions look larger.
- Ask clarifying questions for hidden ingredients, cooking oil, sauces, broth, shared dishes, or unclear portion size.

Text or voice:

- Parse the meal item by item.
- Ask for missing high-impact details: cooked vs raw weight, portion count, oil/butter, broth consumed, sauce amount, drink size, or brand.
- Treat direct corrections as authoritative and update the same meal.

Nutrition label:

- Read values from the label.
- Use per-serving values multiplied by servings consumed, or whole-package values when the user ate the whole package.
- For branded packaged foods, prefer the label or verified product nutrition over generic estimates.

## Estimate Nutrition

Calculate each item's calories, protein, carbs, and fat. Add optional nutrients when useful: saturated fat, fiber, sugar, sodium, water, or caffeine.

If the user asks for higher accuracy for branded products, search reliable product pages or nutrition databases and note any regional uncertainty.

## Save A Meal

Build a JSON object and save with:

```bash
fitness meals save --meal-file /tmp/meal.json --json
```

Required JSON fields:

```json
{
  "eaten_at": "2026-05-23T13:10:00+08:00",
  "meal_type": "breakfast",
  "items": [
    {
      "name": "Greek yogurt",
      "portion_description": "250 g",
      "calories": 150,
      "protein_g": 25,
      "carbs_g": 9,
      "fat_g": 0
    }
  ],
  "total_calories": 150,
  "notes": "logged from photo; portions estimated",
  "source": "photo"
}
```

Rules:

- Do not include `quantity`; use `portion_description`.
- Sum `total_calories` from items.
- Valid `meal_type` values are usually `breakfast`, `lunch`, `dinner`, and `snack`.
- Prefer a temporary JSON file and remove it after a successful save.
- Capture and reuse the returned `meal_id` for corrections.

## Update Or Correct A Meal

For corrections, rebuild the full updated meal payload and call:

```bash
fitness meals update --meal-id <meal_id> --meal-update-file /tmp/meal.json --json
```

Use the same meal when the user adds items after confirming or correcting a meal. Do not create a new meal for each addition unless the user clearly starts a separate meal.

When the user says "half a banana", "only one slice", or similar, apply the correction directly, recalculate totals, update the log, and present the new numbers.

## Confirm A Meal

Confirmation signals include "yes", "confirm", "save it", "about right", and similar acceptance.

After confirmation, update the meal status:

```bash
fitness meals update --meal-id <meal_id> --meal-update-file /tmp/meal-confirmed.json --json
```

The update payload should include the current full meal data plus:

```json
{
  "status": "confirmed",
  "confirmed_by_user": true
}
```

## Daily Context

Useful commands before or after logging:

```bash
fitness context brief --json
fitness targets explain --as-of YYYY-MM-DD --json
fitness meals summary --start YYYY-MM-DD --end YYYY-MM-DD --json
fitness meals list --start YYYY-MM-DD --end YYYY-MM-DD --json
```

If a daily nutrition summary lags behind a recent save, check `fitness meals list` before assuming the meal failed.

## Presenting Results

Use concise plain text, especially for chat or mobile contexts:

```text
Saved lunch: 640 cal / 42P / 58C / 22F

Items:
- Chicken rice: 520 cal / 36P / 55C / 14F
- Iced tea: 120 cal / 0P / 30C / 0F
```

For meal ideas or variations, use short numbered options with ingredients and totals. Avoid markdown tables unless the user specifically wants them.

## Common Pitfalls

- Do not save from a photo unless the user asked to log it.
- Do not let a surprise image interrupt an unrelated conversation; ask what they want done with it.
- Always include a timezone offset in `eaten_at`.
- Clarify raw vs cooked weights for meat.
- Ask whether broth, sauces, oils, or shared portions were consumed.
- When a user questions a total, review the calculation item by item instead of defending the estimate.
- Expect multiple correction rounds for restaurant meals, hot pot, noodle soup, buffets, and family-style dishes.
