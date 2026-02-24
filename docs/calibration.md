# Model Calibration

SubtitleToolkit can **calibrate** any AI model before translation to find
the optimal chunk size and concurrency settings automatically.

---

## What is calibration?

Calibration probes your selected model with small real translation requests
and measures two things:

| Setting | What it controls |
|---|---|
| **Chunk size** | How many subtitle lines are sent per API request |
| **Concurrent workers** | How many requests run in parallel |

Getting these right matters:

- **Chunk too large** → the model truncates its response, losing translated lines silently
- **Too many workers** → your API plan's rate limit is exceeded, causing errors and slow retries
- **Calibrated values** → maximum throughput with zero truncation errors

---

## How to calibrate

### From the Translate Configuration panel

1. Expand the **Translate Configuration** panel in the main window
2. Select your **engine** and **model**
3. Look for the indicator next to the model selector:
   - `○` (grey) — not yet calibrated
   - `✓` (green) — calibrated, hover for details
4. Click **Calibrate…** (or **Re-calibrate** if already done)
5. Confirm the cost warning and click **Start Calibration**

### From the menu

**Tools → Calibrate Model…** (`Ctrl+Shift+C`)

This opens the same dialog, pre-filled with the model currently selected
in the Translate panel.

---

## How calibration works

### Phase 1 — Chunk size

Sends translation batches of increasing size:
`5 → 10 → 20 → 30 → 50 → 75 → 100 subtitles`

For each size the response is checked for completeness (≥ 90 % of sent items
returned).  The sweep stops at the first failure and saves the last fully-successful
size as the recommended chunk size.

### Phase 2 — Concurrent workers

Fires 1, 2, 3, 4, then 5 identical small requests simultaneously.
If a rate-limit error is detected the sweep stops and the last fully-successful
concurrency level is saved.

### Test data

Both phases use a fixed 80-sentence English → Spanish test set unrelated to
your actual subtitle content.  It is designed to produce varied token lengths
that are representative of real subtitle files.

---

## Cost

Calibration makes real API calls.  Typical costs:

| Model | Typical cost |
|---|---|
| GPT-4o-mini | < $0.01 |
| GPT-4o | ~$0.03 – $0.05 |
| Claude Haiku | < $0.01 |
| Claude Sonnet | ~$0.03 – $0.05 |
| Groq / DeepSeek / Mistral | ~$0.001 – $0.01 |

The dialog shows a dollar estimate before you start (if you have set model prices
in the **Translate Configuration → Price (per model)** fields).

Worst case (all probes succeed): ≈ 6 000 input + 4 000 output tokens.
Best case (limits found early): fewer tokens.

---

## After calibration

Results are stored per-model in application settings.

When you select a calibrated model in the **Translate Configuration** panel:

- The **chunk size** and **worker count** spinboxes are automatically set to
  the calibrated values
- The **✓** indicator appears with a tooltip showing the calibration date and values

The calibrated values replace the previous per-model profile for that model.

---

## When to re-calibrate

- After upgrading your API plan (higher rate limits → more workers may be safe)
- If translated files have missing subtitle lines (chunk may be too large for current quotas)
- If the log shows frequent rate-limit retries (workers may be too high)
- After switching to a fine-tuned or updated version of a model

---

## Notes

- Calibration is **optional** — the defaults (chunk 20, 2 workers) work for
  most models without calibration.
- Results are **per-model name**: `gpt-4o-mini` and `gpt-4o` have separate profiles.
- You can open the calibration dialog for any model, not just the one currently
  selected for translation.
- The **Documentation** tab inside the calibration dialog contains a condensed
  version of this page.
