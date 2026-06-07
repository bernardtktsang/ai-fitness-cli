---
name: meal-logging
description: Log, update, and review meals with the AI Fitness CLI from food photos, text descriptions, voice corrections, or nutrition labels. Use when a user wants nutrition estimates saved, corrected, or compared against daily targets.
---

# Meal Logging

Use this skill when the user wants to estimate, save, update, or review meal logs through the `fitness` CLI.

## Ground Rules

- Use the CLI for meal reads and writes. Run `fitness doctor` if setup is uncertain.
- If the user sends a meal photo or meal description in a meal-logging context, estimate and save it directly. Treat corrections afterward as normal updates.
- Mark uncertain photo-based estimates as approximate in `notes` and invite corrections after saving.
- Do not ask for the meal time when the user says they just ate it. Omit timestamp fields and let the backend stamp the meal at save time.
- If the user gives a past/specific meal time, use `eaten_at` as a bare local datetime and include `timezone` when known, e.g. `"eaten_at": "2026-05-23T13:10:00", "timezone": "Asia/Hong_Kong"`.
- If `eaten_at` is a bare local datetime and `timezone` is omitted, the backend uses the user profile timezone.
- Offset-only `eaten_at` is accepted for exact absolute timestamps, but never combine an offset datetime with `timezone`.

## Analyze Input

Photo:

- Identify every visible item.
- Estimate portions using scale references such as fork, spoon, mug, hand, plate rim, or container size.
- Be conservative with styled overhead photos, which often make portions look larger.
- If hidden ingredients, oil, sauces, broth, shared dishes, or portion size are unclear, make a reasonable estimate and note the uncertainty. Ask only when the missing detail would materially change the log and cannot be reasonably estimated.

Text or voice:

- Parse the meal item by item.
- Estimate missing details such as cooked vs raw weight, portion count, oil/butter, broth consumed, sauce amount, drink size, or brand when context is sufficient. Ask only for details that would materially change the log.
- Treat direct corrections as authoritative and update the same meal.

Nutrition label:

- Read values from the label.
- Use per-serving values multiplied by servings consumed, or whole-package values when the user ate the whole package.
- For branded packaged foods, prefer the label or verified product nutrition over generic estimates.

## Estimate Nutrition

Calculate each item's calories, protein, carbs, and fat. The backend validates
meal JSON keys strictly, so use only the exact flat field names below. Do not
send nested `macros` or `nutrients` objects.

When time permits, check personal food history before re-estimating common or
recurring foods:

```bash
fitness foods search "rice" --json
fitness foods get "greek yogurt" --json
```

Use those results as prior logged references for this user, especially for
usual portions and repeated home-cooked foods. They are not a generic food
database, product-label source, or per-100g nutrition table.

Item-level nutrition keys:

- `calories`
- `protein_g`
- `carbs_g`
- `fat_g`
- `fiber_g`
- `sugar_g`
- `sodium_mg`
- `saturated_fat_g`
- `caffeine_mg`
- `water_ml`
- `confidence`

Do not send meal-level nutrition fields such as `total_calories`, meal-level macros, or meal-level `confidence`.

Add optional nutrients when useful:

- `caffeine_mg` - coffee, tea, pre-workout (black coffee ~95 mg/cup)
- `fiber_g` - whole grains, vegetables, fruits
- `sodium_mg` - salt/sodium tracking
- `sugar_g` - total sugars
- `water_ml` - hydration tracking
- `saturated_fat_g` - saturated fat breakdown

Include optional item fields in the meal JSON when the user mentions them (e.g.,
"log a black coffee with caffeine").

If the user asks for higher accuracy for branded products, search reliable product pages or nutrition databases and note any regional uncertainty.

## Save A Meal

Build a JSON object and save with:

```bash
fitness meals save --file /tmp/meal.json --json
```

Example JSON:

```json
{
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
  "notes": "logged from photo; portions estimated",
  "source": "photo"
}
```

Timestamp rules:

- For "just now" meals, omit `eaten_at`; the backend logs the save time using the user timezone for agent-facing output.
- For earlier/scheduled local meals, send `eaten_at` without an offset, plus `timezone` if known.
- If `timezone` is omitted for a bare local `eaten_at`, the backend uses the user profile timezone.
- For externally sourced absolute times, send offset-only `eaten_at` with no `timezone`.

Rules:

- Do not include `quantity`; use `portion_description`.
- Do not include nested `macros` or `nutrients`; use the flat keys listed above.
- Do not include meal-level nutrition fields such as `total_calories`, `protein_g`, `carbs_g`, or `fat_g`.
- Valid `meal_type` values are usually `breakfast`, `lunch`, `dinner`, and `snack`.
- Prefer a temporary JSON file and remove it after a successful save.
- Capture and reuse the returned `meal_id` for corrections.

## Update Or Correct A Meal

For corrections, rebuild the full updated meal payload and call:

```bash
fitness meals update --meal-id <meal_id> --file /tmp/meal.json --json
```

Use the same meal when the user adds items after saving or correcting a meal. Do not create a new meal for each addition unless the user clearly starts a separate meal.

When the user says "half a banana", "only one slice", or similar, apply the correction directly, recalculate totals, update the log, and present the new numbers.

**Update recalculation behavior:** `fitness meals update` recalculates
meal-level aggregate fields from the provided `items` array automatically: `total_calories`, `protein_g`, `carbs_g`, `fat_g`,
`fiber_g`, `sugar_g`, `sodium_mg`, `saturated_fat_g`, `caffeine_mg`, and
`water_ml`. The response includes a `nutrition_integrity` block:

```json
"nutrition_integrity": {
  "item_calories_complete": true,
  "item_total_mismatch": false,
  "known_item_calories": 995.0,
  "missing_item_calorie_count": 0,
  "total_calories_source": "item_sum",
  "warnings": []
}
```

When `item_total_mismatch` is `false` and `total_calories_source` is `"item_sum"`, the totals match the item-level data exactly.

**Save vs Update flag difference (common pitfall):**
- Both `meals save` and `meals update` accept the shared `--file` alias.
- The generated long-form flags are `--meal-file` for save and `--meal-update-file` for update.

Prefer `--file` unless you specifically need the long-form flag.

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

- In meal-logging contexts, do not block on confirmation before saving a photo-based estimate; save with uncertainty in `notes` and correct afterward if needed.
- If an image appears in a clearly unrelated conversation, briefly infer whether it is a meal-log request from context before asking what to do.
- **Meal timestamps are optional on save:** For meals being logged right now, omit all timestamp fields and let the backend stamp the save time.
- **Use local meal time for past/specified meals:** Use `eaten_at` as a bare datetime such as `2026-05-17T19:00:00` and `timezone` such as `Asia/Hong_Kong`.
- **Bare local time fallback:** If `eaten_at` is a bare local datetime and `timezone` is omitted, the backend uses the user profile timezone.
- **Absolute timestamps may use offsets:** Offset-only `eaten_at` such as `2026-05-17T12:00:00+08:00` or `2026-05-17T12:00:00Z` is accepted, but do not include `timezone` with it.
- **Meal item field `quantity` is rejected:** Do not include `quantity` in meal items. Use `portion_description` (optional string) instead, but the most reliable approach is to encode portion info directly in the item `name` (e.g., "Hash brown (half)").
- **No nested macro/nutrient objects:** Do not send `macros`, `nutrients`, `nutrition`, or similar nested objects. The backend accepts flat keys only and will reject unknown keys.
- **Calorie key:** Use `calories` inside each item. Do not use meal-level `calories`, meal-level `total_calories`, or item-level `total_calories`.
- **Meal JSON timestamp fields:** Use `eaten_at` for local wall-clock meal times and include `timezone`; never use `local_eaten_at`, `eaten_at_timezone`, or `logged_at`.
- **Date arguments:** Most commands use `--start` and `--end` (not `--start-date`). Example: `fitness meals list --start 2026-05-10 --end 2026-05-10` - using `--start-date` will fail with a missing-argument error.
- **Assume save time for just-now meals:** When the user confirms they just ate a meal (e.g., "yup," "just ate it," "just now"), do not ask what time and do not invent a timestamp. Only ask for a specific time if the user says they ate it much earlier or later.
- Estimate raw vs cooked weights for meat when not specified, and note the assumption.
- Estimate broth, sauces, oils, or shared portions when not specified, and note the assumption.
- When a user questions a total, review the calculation item by item instead of defending the estimate.
- Expect multiple correction rounds for restaurant meals, hot pot, noodle soup, buffets, and family-style dishes.
