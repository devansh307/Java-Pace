# TDC Fix Map — Exact Locations & Replacements

Covers all four TDC artifacts in the agent JSON:
- A. `capabilities[tdc_followup].system_prompt`
- B. `capabilities[tdc].system_prompt`
- C. `td_followup_context_setting` (pre-call function — builds the Transcript-1 greeting)
- D. `tdc_context_setting` (pre-call function)

---

## A. `tdc_followup` system prompt

### A1. ⚠️ ROOT CAUSE OF TRANSCRIPT-1 STATE COLLISION — hardcoded no-show transition

**Current text (second OPENING block):**
```
OPENING
Always greet first using:
{greeting_and_initial_line}
Then transition directly:
"आपकी test drive आज scheduled थी, लेकिन आप hub नहीं आ पाए — सब ठीक है ना?"
```
**Problems:**
1. `{greeting_and_initial_line}` is injected VERBATIM by the pre-call function and already explains the real scenario (car booked by someone else / auto-cancelled / home-TD cancelled). The static "Then transition directly" line then forces the *no-show* framing on top — in Transcript 1 the bot spoke the car-unavailable greeting, the customer accepted ("दिखा दो"), and the bot then said this hardcoded line anyway. Two contradictory premises in consecutive turns.
2. "आज" is hardcoded — the TD was on 9 June, the call on 10 June. Wrong date spoken.
3. It contradicts `{next_steps}` ("Car is BOOKED. Pivot to pitching similar cars.").

**Replacement:**
```
OPENING
Speak {greeting_and_initial_line} VERBATIM as the first content turn, then PAUSE.
After the customer responds, follow {next_steps} ONLY.

NEVER speak any no-show line ("आप hub नहीं आ पाए — सब ठीक है ना?") if
{greeting_and_initial_line} already explained the situation (car unavailable,
auto-cancelled, or home-TD cancelled). The no-show probe exists ONLY for the
standard case where the car is still available AND {next_steps} asks you to probe.
Once the customer accepts a pivot (e.g., "दिखा दो"), LOCK that branch — do not
return to confirmation, no-show, or any other branch.
```

### A2. Duplicate / contradictory OPENING blocks
There are TWO opening sections: the `%Callflow% ## OPENING` block (full intro: "नमस्ते... आर्यन बोल रहा हूँ... दो मिनट बात हो सकती है?") and the second `OPENING` block (A1). Meanwhile **Rule 3 says "Start directly — no name or address intro"** — directly contradicting the Callflow intro. Merge into ONE opening section: intro line → wait → verbatim greeting → follow next_steps. Delete Rule 3 or the intro, whichever matches business intent.

### A3. Feminine self-reference in CLOSING BLOCK
**Current:** `"क्या मैं आपकी कुछ और help कर सकती हूँ?"`
**Fix:** `"क्या मैं आपकी कुछ और help कर सकता हूँ?"` — violates the male-agent rule at the top of this same prompt.

### A4. Malformed SSML break tags (3 occurrences)
**Current:** `<break time<="0.2s" />` (cancellation accept, callback confirm, closing line).
`time<=` is invalid SSML — TTS may read it aloud or drop the tag.
**Fix:** `<break time="0.2s"/>` everywhere.

### A5. Missing blocks to add
- **AMBIGUITY GATE** ("नई/पुरानी", "वो वाली", "दूसरी वाली") — clarify-before-acting, see `prompt-patches-tdc-loan-feedback.md` Patch 1. Must sit ABOVE the CAR CHANGE REQUEST section, because that section currently triggers `switch_capability("sql_followup")` "Immediately" on phrases like "दूसरी car देखनी है" — which is how ambiguous utterances become unwanted pitches.
- **Context-aware confirmation greeting** (`{last_call_summary}`) — Patch 3.
- **Pivot-with-context rule:** when switching to `sql_followup` because the booked car is gone, first ask ONE bridging question ("आप वैसी ही {model} देखना चाहेंगे या same budget में और options भी?") and carry the cancelled car's make/model/budget into the search — Transcript 1 pitched blind Kwids without this.
- Rule numbering jumps 5 → 8 (missing 6–7) — clean up.

---

## B. `tdc` system prompt

### B1. ⚠️ EMPTY INTERRUPTION GUARDRAIL block
**Current:**
```
## INTERRUPTION GUARDRAIL

If the user interrupts before the full confirmation question is complete:
```
The block ends there — **no instruction exists**. This is an unfinished prompt section.
**Fix:** complete it with the post-interruption essential-disclosure rule (T2 remediation Fix 4):
```
- Stop the sentence immediately and address the interruption.
- Before answering any car-attribute question, re-anchor WHICH car is being
  discussed in one short clause if it was not yet spoken in full.
- Then resume ONLY the incomplete confirmation thought:
  "मैं बस आपकी {date} की test drive confirm कर रहा था — आप {time} पर आ पाएंगे ना?"
- Never restart the intro.
```

### B2. Eager capability switch without clarification
Rule 5 + CAR CHANGE REQUEST both say switch to `sql_followup` "Immediately" on "दूसरी car देखनी है". Insert the AMBIGUITY GATE above these sections (same as A5) so ambiguous phrases ("नई पुरानी?", "वो वाली") trigger ONE clarification first; only explicit car-change intent switches.

### B3. Malformed SSML break tags (2 occurrences)
`<break time<="0.2s" />` in the out-of-station callback line and the closing line → fix to `<break time="0.2s"/>`.

### B4. Duplicate OPENING sections
Two OPENING blocks here too (Callflow block at top; second one before "VALID CONFIRMATION DETECTION"). Merge into one; keep the confirmation ask `"बस आपकी test drive confirm करनी थी — आप {scheduled_time} पर {hub_name} आ पाएंगे ना?"` as the single post-intro line.

### B5. Missing blocks to add (same as A5)
- AMBIGUITY GATE, `{last_call_summary}` context greeting, pivot-with-context rule.
- Loan-discussed follow-through line after confirmation (if last call covered loan/EMI): "जो loan estimate discuss हुआ था, hub पर finance team exact figures बता देगी — documents साथ ले आइएगा।"

---

## C. `td_followup_context_setting` (pre-call function)

### C1. ⚠️ "Spinny Spinny Park" duplication
**Current (greeting builder):**
```python
loc_text = "Home Test Drive" if cancelled_visit["at_home"] else f"Spinny {cancelled_visit['hub_name'] or 'hub'} पे test drive"
```
`hub_name` is already "Spinny Park, Jaipur" → spoken as "Spinny Spinny Park, Jaipur पे test drive" (heard verbatim in Transcript 1).
**Fix:**
```python
hub = cancelled_visit['hub_name'] or 'hub'
hub_display = hub if hub.lower().startswith('spinny') else f"Spinny {hub}"
loc_text = "Home Test Drive" if cancelled_visit["at_home"] else f"{hub_display} पे test drive"
```

### C2. ⚠️ Malformed 3-second break in ALL greeting templates (4 occurrences)
**Current:** `<break time="3.0" />` — (a) missing the `s` unit → invalid SSML; (b) even if honored, 3 seconds of dead air mid-greeting made the customer say "हेलो?" in Transcript 1.
**Fix:** replace all 4 with `<break time="0.5s"/>` (or remove — the prompt instructs PAUSE after the greeting anyway).

### C3. No empathy in the booked-car greeting
**Current:** "...पर वो कार अभी available नहीं है, किसी और ने book कर ली है। मैं आपको similar cars दिखा देता हूँ। क्या आप देखना चाहेंगे"
A customer's *booked* TD car was given away — needs one apology/reassurance beat.
**Fix (greeting template):**
```
"...पर sorry, वो कार किसी और ने book कर ली है — बहुत fast-selling model थी। <break time="0.3s"/>
आपका टाइम waste ना हो, इसलिए मैं उसी जैसी कुछ अच्छी options आपके लिए ready रखी हैं। क्या दिखाऊँ?"
```

### C4. `next_steps` for the booked-car case is under-specified
**Current:** `"Car is BOOKED. Pivot to pitching similar cars. move to car change request section if user agrees"`
This sends the model straight into a blind `switch_capability("sql_followup")` pitch (what happened in Transcript 1).
**Fix:**
```python
next_steps = (
    f"Car is BOOKED. The cancelled car was {car_name} (Lead ID: {cancelled_visit['sell_lead_id']}). "
    "If the customer agrees to see similar cars: ask ONE bridging question first — "
    "'आप वैसी ही {car_name} देखना चाहेंगे या same budget में और options भी?' — "
    "then switch_capability('sql_followup') carrying make/model/budget of the cancelled car as starting filters. "
    "Do NOT pitch without this context."
)
```

### C5. Security hygiene
A long-lived bearer JWT is hardcoded in the function source. Move to a platform secret/env reference — any config export (like the one analyzed here) leaks a valid internal API token.

---

## D. `tdc_context_setting` (pre-call function)

### D1. Same malformed break tag — 8 occurrences
`<break time="3.0" />` in every greeting variant (both-cars-booked, one-booked-one-available, car-unavailable, home-TD, day-confirmation, loan variant). Fix all to `<break time="0.5s"/>`.

### D2. Same blunt booked-car phrasing
"पर वो दोनों कार्स अभी available नहीं हैं" / "तो किसी और ने book कर ली है" — add the same one-line apology beat as C3 in the 3 booked/unavailable variants.

### D3. Hub display check
This function uses `v.get("hub_name", "hub")` WITHOUT prepending "Spinny" — no duplication bug here, but verify spoken output is natural ("Spinny Park, Jaipur पर Test Drive") and apply the C1 helper if any template later prepends the brand.

---

## Priority order

| # | Fix | Why first |
|---|---|---|
| 1 | A1 (delete hardcoded no-show transition + branch lock) | Direct root cause of the Transcript-1 confusion the customer escalated |
| 2 | C2 + D1 (3.0 break → 0.5s) | Trivial edit; removes dead air in every TDC call |
| 3 | C1 (Spinny Spinny) | Trivial edit; heard verbatim by customers |
| 4 | A5/B2/B5 (ambiguity gate + context greeting + pivot-with-context) | The two feedback items |
| 5 | B1 (empty interruption guardrail) | Unfinished block; pairs with T2 Fix 4 |
| 6 | C3/C4/D2 (empathy + next_steps context) | Conversion quality on lost-car calls |
| 7 | A3/A4/B3/B4 (feminine form, malformed tags, duplicate openings) | Hygiene |
| 8 | C5 (hardcoded JWT) | Security |
