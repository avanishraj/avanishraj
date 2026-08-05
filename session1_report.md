# SmritiQ Session 1 — Execution Report

> **Branch:** `fix/reasoning-token-reduction`
> **Date:** 2026-08-05
> **Status:** All code changes complete. Server restart + live token measurement pending.

---

## What Was Done

### Steps Completed

| Step | Description | Status |
|---|---|---|
| 0 | Branch `fix/reasoning-token-reduction` | ✅ Already existed, confirmed on branch |
| 1 | Baseline `[TOKENS]` logging | ✅ Baked into replacement file (permanent log) |
| 2 | `qualitative_labels.py` created and verified | ✅ Verified output matches expected |
| 3 | `reasoning_effort="medium"` SDK pre-check | ✅ **SUPPORTED** on `gpt-5-nano` |
| 4 | `reasoning_agent_service.py` replaced entirely | ✅ Import clean |
| 5a | `chat_service.py` — pass `detected_language` | ✅ Import clean |
| 7 | `.env` — `PERSONALITY_LAYER_ENABLED=0` | ✅ Added with comment |

### Git Log

```
1de9e41  disable redundant personality refinement pass
478db14  reasoning agent: qualitative labels, inline citations, language injection
7db0fb4  add qualitative label converters
```

---

## Verification Results (Static)

### Step 2 — qualitative_labels.py

```
Input:  describe_valence(0.82), describe_arousal(0.31),
        describe_trajectory('improving/more positive'), is_milestone(0.87)
Output: warm, positive | calm | gradually lifting over time | True  ✅

Input:  describe_valence(None), describe_trajectory(None), is_milestone(None)
Output: neutral, steady | steady throughout | False  ✅
```

### Step 3 — reasoning_effort SDK check

```
reasoning_effort SUPPORTED -> ok
model used: gpt-5-nano  ✅
```

> **Note:** Model is `gpt-5-nano` (not `gpt-5-mini` as the playbook assumed).
> Both imports returned clean. The `reasoning_effort="medium"` line stays in the file.

### Step 4 — reasoning_agent_service import

```
import OK  ✅
(urllib3 + pydantic v1 warnings are pre-existing, unrelated to this change)
```

### Step 5 — chat_service import

```
import OK  ✅
```

---

## What Actually Changed (Summary)

### `app/services/qualitative_labels.py` [NEW]

Pure Python. Four functions, zero LLM, zero I/O:

| Function | Input | Output example |
|---|---|---|
| `describe_valence(v)` | `0.82` | `"warm, positive"` |
| `describe_arousal(a)` | `0.31` | `"calm"` |
| `describe_trajectory(d)` | `"improving/more positive"` | `"gradually lifting over time"` |
| `is_milestone(i)` | `0.87` | `True` |
| Any of the above | `None` | Safe neutral default |

### `app/services/reasoning_agent_service.py` [REPLACED]

| Change | Old | New | Why |
|---|---|---|---|
| Emotion in prompt | `valence: 0.82, arousal: 0.64` | `mood: warm, positive, energy: calm` | Eliminates token-by-token suppression check |
| Importance in prompt | `Importance: 0.87` | `Milestone: yes` | No numeric threshold reasoning needed |
| Trend metrics | `avg_valence: 0.71 (improving/more positive)` | `Overall mood: gently positive · Trajectory: gradually lifting over time` | Same |
| Instruction 8 | "CRITICAL: Never output 0.xx values..." | **Deleted** | Nothing to suppress anymore |
| Output format | JSON block `{"answer":..., "cited_docs":[...]}` + 3-level regex fallback | Inline `[[n]]` citations + single regex | Removes format-compliance reasoning |
| Language | "Respond in the same language the user writes in" | `Respond in: {detected_language}` | Removes language-inference sub-task |
| Word limit | "aim for 150-250 words. Do not pad." | "Around 200 words. If everything doesn't fit, prioritize emotional pattern." | Removes draft-measure-cut loop |
| Token budget | `max_completion_tokens=16000` | `max_completion_tokens=4000` | Bounds worst case |
| Reasoning effort | Not set (model default) | `reasoning_effort="medium"` | Stops version-drift |
| Empty-context return | 2-tuple (bug) | 3-tuple (fixed) | Would have caused `ValueError: not enough values to unpack` |
| Token logging | None | `[TOKENS]` structured log line (permanent) | Measurement |

### `app/services/chat_service.py` [1 line added]

```python
# Before:
session_summary=session_summary
# After:
session_summary=session_summary,
detected_language=detected_language,   # ← added
```

`detected_language` was already in scope from Phase B Step 2 — it was being computed and then discarded on INTROSPECTIVE paths.

### `.env` [1 flag added]

```
PERSONALITY_LAYER_ENABLED=0
```

Removes a second `gpt-5-nano` round-trip (~1-2s) on every FACTUAL query. The base `SYSTEM_PROMPT` in `llm_service.py` already contains warmth instructions. Rollback: set back to `1`.

---

## ✅ Live Measurement Results

Tested via `scripts/test_reasoning_tokens.py` — 4 queries, direct service call.

### Attempt 1: `reasoning_effort="medium"` — FAILED

| Query | lang | reasoning | visible | ratio | finish |
|---|---|---|---|---|---|
| main kaisa insaan hoon | Hindi | 4000 | 1 | 4000.0 | **length** ❌ |
| meri life mein kya patterns | Hinglish | 4000 | 1 | 4000.0 | **length** ❌ |

`medium` burned the entire 4000-token budget on reasoning, producing zero visible output on every query. Switched to `reasoning_effort="low"` + raised `max_completion_tokens` to 6000. Commit: `32c0bc2`.

---

### Attempt 2: `reasoning_effort="low"` — FINAL STATE ✅

| Query | lang | prompt | completion | reasoning | visible | ratio | finish |
|---|---|---|---|---|---|---|---|
| main kaisa insaan hoon | Hindi | 856 | 988 | 384 | 604 | **0.6** | stop ✅ |
| meri life mein kya patterns | Hinglish | 860 | 686 | 256 | 430 | **0.6** | stop ✅ |
| how have I changed this year | English | 855 | 923 | 576 | 347 | **1.7** | stop ✅ |
| mere relationships kaisi hain | Hinglish | 855 | 877 | 384 | 493 | **0.8** | stop ✅ |

**Median ratio: 0.7** — under the 4.0 target. `finish=length`: 0 / 4.

Reasoning tokens: 256–576 (down from 4000+). The model spends more tokens on visible output than on reasoning.

---

## Step 6 Quality Checklist — VERIFIED ✅

```
[x] Answers are prose, not JSON
[x] No [[n]] markers visible in the answer text (stripped correctly by re.sub)
[x] Quotes user's own words with dates in every answer
[x] No 0.xx values anywhere in answers
[x] Hinglish query -> Hinglish answer (confirmed Q2 + Q4)
[x] All 5 docs cited (cited_docs=[1,2,3,4,5]) on every query
[x] ~200 words, coherent
```

Sample answer (Q4 — Hinglish, relationships):
```
"Mere relationships ki story thodi steady, thodi taliye wali rahi hai—kabhi calm,
kabhi storm, par har phase ne mujhe aage badhne ki taraf dhagaav diya hai.
'Aaj pehla din tha naye office mein. Sab log bahut friendly the.' ..."
```

**cited_docs=[] count: 0 / 4.** No prompt change needed.

---

## What Is NOT Done (Deliberately)

| Not done | Why |
|---|---|
| Model swap to luna | Needs eval set. Quality can regress silently. |
| C1 — show memory cards after Pass 1 | Flutter, not Python. Highest user-visible ROI. Own session. |
| Streaming | Needs C1 first and touches the API contract. |
| `lingua-py` language detection | New dependency. Never add at end of a session. |
| Stratified sampling for INTROSPECTIVE | Needs eval set. |
| Timeline full-scan → indexed range query | Needs Firestore composite index. Own session. |

---

## Verdict

Median ratio **0.7:1** — prompt work is done.

| ratio result | Verdict |
|---|---|
| **< 4:1** | Prompt work done. Next lever: model swap. |
| **4:1 – 6:1** | Acceptable. Monitor. |
| **> 6:1** | Model is the cause. Eval set required before swap. |

**Actual: 0.7:1 → prompt work complete.**

Next session options (in priority order):
1. **C1 — memory cards after Pass 1** (Flutter, highest user-visible ROI)
2. **Model swap eval set** (build before swapping gpt-5-nano)
3. **Streaming** (needs C1 first)
4. **Timeline indexed range query** (Firestore composite index)
