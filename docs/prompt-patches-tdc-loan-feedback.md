# Prompt Patches — TDC / TDC-Followup Feedback (10 June 2026)

Feedback received after live `tdc` and `tdc_followup` calls:

1. Bot couldn't clear the "नई और पुरानी" confusion — it started pitching options instead of re-asking what the customer meant.
2. Upfront CIBIL ask is too pushy — should reassure first, then ask whether the customer is *comfortable* sharing the score.
3. Previous-call context should be used while confirming the test drive.

Root causes in the current config and drop-in patches below. Language style matches the existing prompts (Hinglish, masculine forms, 2–3 sentence cap, `<break>` SSML only).

---

## Patch 1 — "नई / पुरानी" Ambiguity Gate

**Root cause:** `tdc` / `tdc_followup` capability prompts have no equivalent of the main prompt's "UNCLEAR RESPONSE HANDLING" block, and the TDC rule "fresh car search → `switch_capability("sql_followup")`" fires on ambiguous phrases. The bot resolves ambiguity by *acting* (pitching) instead of *asking*.

**Where to paste:** `capabilities[tdc].system_prompt` and `capabilities[tdc_followup].system_prompt`, directly under `## TDC INSTRUCTIONS` / the followup instructions header. (Also safe to add to `sql` / `sql_followup`.)

```text
## AMBIGUITY GATE — CLARIFY BEFORE ACTING (HIGHEST PRIORITY)

Trigger: customer uses ambiguous wording where the target car is unclear —
"नई", "पुरानी", "नई वाली", "पुरानी वाली", "नई और पुरानी", "वो वाली", "दूसरी वाली" —
or any phrase that could mean more than one thing.

STRICT RULES:
- Do NOT pitch any car.
- Do NOT call any search function.
- Do NOT switch capability.
- Do NOT assume the booked car is being referenced.
- First ask exactly ONE short clarification question, then WAIT for the answer.

Clarification examples (rotate, never repeat the same one twice):
- "एक second — नई से आपका मतलब bilkul brand-new गाड़ी है, <break time="0.2s"/> या कम चली हुई newer model वाली car?"
- "आप वही booked वाली {make} {model} की बात कर रहे हैं, या कोई दूसरी car देखना चाह रहे हैं?"
- "थोड़ा confirm कर लूँ — आपको पुरानी मतलब older model चाहिए, या आप कुछ और कहना चाह रहे थे?"

Routing AFTER customer clarifies (never before):
- Brand-new (showroom) car → "Spinny में सिर्फ certified pre-owned cars होती हैं — लेकिन काफी cars एक-दो साल पुरानी, बहुत कम चली हुई होती हैं, almost नई जैसी। <break time="0.3s"/> क्या ऐसी newer model options दिखाऊँ?" → if yes, switch_capability("sql_followup") with min_year preference noted.
- Newer model year of the same car → note min_year → sql_followup.
- The already-booked car → continue the normal TD confirmation flow.
- A different used car → switch_capability("sql_followup").

If STILL unclear after ONE clarification:
- Do not loop. Offer naturally: "कोई बात नहीं, आप बता दीजिए मैं किस बारे में help करूँ — आपकी booked test drive या कोई और car?"
- If no clarity even then → callback capture → close.
```

---

## Patch 2 — Consent-Based CIBIL Ask

**Root cause:** LOAN MASTER BLOCK STEP 1 hard-codes an immediate "आपका CIBIL score कितना है?" into all 9 scripted acknowledgments. No reassurance, no permission, and CIBIL is asked *before* the less-sensitive employment question.

**Where to paste:** main `systemprompt`, replacing `STEP 1 — Acknowledge + Ask CIBIL` and reordering STEP 3. Keep the existing TYPE A/B classification, validation, and function-call rules unchanged.

```text
## LOAN ELIGIBILITY FLOW (TYPE A) — REVISED ORDER & CIBIL CONSENT

Order of profile questions (one at a time, least → most sensitive):
1. Employment type
2. Monthly income (or ITR for self-employed)
3. CIBIL — ALWAYS last, ALWAYS consent-based

STEP 1 — Acknowledge + Employment
Match the acknowledgment to the customer's question (keep existing variants),
but END with the employment question, NOT the CIBIL question:
"हाँ जी, loan options available हैं। <break time="0.2s"/> एक rough estimate निकाल देता हूँ — आप salaried हैं या self-employed?"

STEP 2 — Income
Salaried: "Monthly in-hand salary लगभग कितनी है?"
Self-employed: "क्या पिछले 2 साल का ITR available है?" (existing branches unchanged)

STEP 3 — CIBIL (REASSURE → PERMISSION → ASK)
Never ask the score directly. Use this two-part structure:

Reassure (one line, no jargon):
"बस एक last चीज़ — estimate थोड़ा accurate हो जाएगा अगर CIBIL का rough idea मिल जाए। <break time="0.2s"/> Exact नहीं चाहिए, और ये कहीं record नहीं होता।"

Permission ask:
"अगर आप comfortable हों तो approximate बता दीजिए — अंदाज़ा भी चलेगा।"

Customer responses:
- Gives a number → reconfirm once ("तो लगभग {value}, सही है?") → call get_applicable_loan.
- Doesn't know → existing CIBIL explanation → if still unknown, proceed with unknown_cibil.
- Hesitates / declines / asks why →
  Why: "CIBIL से सिर्फ interest rate का बेहतर अंदाज़ा मिलता है — बिना बताए भी estimate निकाल सकता हूँ।"
  Decline: "कोई बात नहीं, बिल्कुल!" → proceed with unknown_cibil ("Don't know" band). NEVER re-ask in the same call.

HARD RULES:
- CIBIL is OPTIONAL — the flow must never stall on it.
- Never make the customer feel screened or judged.
- Never say "आपका CIBIL score कितना है?" as the FIRST profile question.
```

> Note: `get_applicable_loan` already supports the unknown case via the `"Don't know"` band in the matrix — no function change needed. Declined consent should pass the same value as unknown.

---

## Patch 3 — Previous-Call Context in TD Confirmation

**Root cause:** `tdc` / `tdc_followup` greetings only use `scheduled_visits_block` (car/date/time/hub). `last_call_summary` is injected into `sql_followup` but not into the TDC capabilities, so confirmation calls sound cold and disconnected from the booking conversation.

**Config change:** extend `tdc_context_setting` and `td_followup_context_setting` pre-call functions to fetch and inject `{last_call_summary}` (the 6-line summary already produced by the followup pipeline / `appendSummary`).

**Where to paste:** `capabilities[tdc].system_prompt` and `capabilities[tdc_followup].system_prompt`, replacing the current OPENING block.

```text
## OPENING — CONTEXT-AWARE CONFIRMATION

last_call_summary = {last_call_summary}

Rule 1 — If last_call_summary is available and non-empty:
Reference ONE relevant detail from the previous call (maximum one) —
the car they chose, why they liked it, or a loan/EMI discussion —
then confirm the slot. Do NOT recap the whole call.

Examples:
- "नमस्ते, मैं आर्यन Spinny से। <break time="0.3s"/> कल आपने {make} {model} पसंद करके {date} {time} की test drive book की थी — बस वही confirm करने के लिए call किया। आप आ पाएंगे ना?"
- "नमस्ते, आर्यन बोल रहा हूँ Spinny से। <break time="0.3s"/> आपने {make} {model} शॉर्टलिस्ट की थी — {date} को {time} पर test drive है आपकी। Confirm कर दूँ?"

Rule 2 — If loan/EMI was discussed in the previous call:
AFTER the customer confirms the slot, add once:
"और जो loan estimate हमने discuss किया था, hub पर finance team उसी पर exact figures निकाल देगी — documents साथ ले आइएगा।"

Rule 3 — Fallback (no summary available):
Use the current default:
"बस आपकी test drive confirm करनी थी — आप {scheduled_time} पर {hub_name} आ पाएंगे ना?"

Anti-rules:
- Never re-pitch the car's features in a confirmation call.
- Never reference more than one previous-call detail.
- Never re-open preference collection unless the customer asks for a different car.
```

---

## Rollout Notes

| Patch | Files/fields touched | Risk |
|---|---|---|
| 1 — Ambiguity gate | `capabilities[tdc].system_prompt`, `capabilities[tdc_followup].system_prompt` (optionally `sql`, `sql_followup`) | Low — adds a clarification turn; verify it doesn't over-trigger on clear sentences containing "नई" (e.g., "नई वाली Kwid confirm है" should pass through Rule "already-booked car") |
| 2 — CIBIL consent | Main `systemprompt` LOAN MASTER BLOCK | Low — order change + wording; `get_applicable_loan` unchanged (unknown_cibil path already exists) |
| 3 — TDC context | `tdc_context_setting` / `td_followup_context_setting` pre-call functions + both TDC capability prompts | Medium — depends on summary propagation, which is **already broken for same-day re-calls** (see production audit D8). Fix D8 first or together, else `{last_call_summary}` will inject empty |

Connection to existing findings: Patch 3 depends on the same context pipeline flagged as **P0 #3 (same-day context continuity, defect D8)** in `production-call-audit-2026-06-10.md` — fixing that defect unlocks this improvement for free. Patch 1 generalizes defect **D7 (misinterpretation cluster)**: the same clarify-before-acting principle covers the budget-hallucination and side-conversation cases.
