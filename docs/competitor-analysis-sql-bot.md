# Competitive Analysis — Our Multi-Capability SQL Bot vs Competitor Voice Bot ("करण", Spinny Jaipur)

**Date:** 10 June 2026
**Our agent:** "SQL" — आर्यन (V369 – Gemini Eleven Labs Male, GPT-4.1, Soniox primary transcriber)
**Competitor agent:** "करण" — observed across 8 outbound Spinny Jaipur call transcripts

---

## 1. Executive Summary

The competitor bot is a strong, broadly capable agent. Its biggest observed edges over our current config are:

1. **Richer loan output** — quotes car-specific loan *amounts*, down-payment *amounts*, and rough *EMI* figures (we only quote LTV %/ROI bands and a generic "around twenty percent" DP line).
2. **Pan-India / cross-city inventory search** — fluidly searches Delhi and Mumbai for a Jaipur lead, including variant-level availability (Thar Roxx 5-door MX1 vs LX 3-door).
3. **Flexible scheduling** — books test drives and *hub visits* up to ~5+ days out, with time windows ("Sunday 10–11 बजे के बीच"); we hard-restrict to today/tomorrow/day-after and push FOMO.
4. **Wider FAQ coverage** — booking status of a specific car, delivery timeline (2–3 days), taxi/commercial RTO conversion guidance, all-inclusive pricing, insurance validity.
5. **Sell-side (C2B) escalation** — handles "inspection done, unhappy with final price" by arranging a procurement-team callback.

Its biggest observed weaknesses — which are direct selling points for us:

1. **No WhatsApp execution.** It explicitly refuses to send photos/details on WhatsApp (T5, T6) and visibly **lost a hot lead** in T6 ("नहीं डाल सकते हो तो बंद करो"). In T7 it then *promises* WhatsApp photos it cannot send — an inconsistency/hallucination. **We have working `send_car_on_whatsapp` and `send_location_on_whatsapp`.**
2. **Prompt leakage** — said "SUV और XUV का अक्सर **transcript** में confusion हो जाता" to a customer (T4), exposing internal instructions.
3. **No mandatory call-ending discipline** — multiple calls end with no callback captured (T2, T6, T7). Our config enforces 3 valid endings (TD booked / callback / notify-when-available).
4. **Skipped preference collection** — pitched ₹10L Hector/Octavia to a Tata Punch (~₹6L) token-attempt lead without ever asking budget (T8).
5. **Factual errors & mismatched pitches** — called a Skoda Octavia an "SUV" (T8); pitched a 1,10,000 km Kwid to a customer who explicitly asked for "कम चली हुई" without flagging the mileage upfront (T6).
6. **Closing-loop repetition** — repeated the same WhatsApp/closing pitch 4–5 turns in a row, with multiple "Are you still there?" (T7); double-fired the closing line (T5); closed while the customer was still asking a question (T1).

---

## 2. Source Material

- **Our config:** `sql-2026-06-10-10-37-50_15e8.json` — agent "SQL", capabilities `sql` (starting), `sql_followup`, `tdc`, `tdc_followup`; in-call functions `get_cars_according_to_user_specifications`, `get_applicable_loan`; post/pre-call functions for lead creation, buy-lead filter updates, WhatsApp car push (`sendMoreCar`), slot instructions, summaries.
- **Competitor:** 8 transcripts (T1–T8) of outbound Hindi/Hinglish calls by "करण" from "Spinny की Jaipur टीम".

---

## 3. Our Bot — Capability Snapshot (from config)

| Area | What we have |
|---|---|
| Capabilities | `sql` (fresh lead), `sql_followup` (re-engage; broken-transaction + last-call-summary greetings; explored-cars section), `tdc` / `tdc_followup` (TD confirmation & reschedule) |
| Inventory search | `get_cars_according_to_user_specifications` (make, model, city, locality, fuel, max_price, transmission, body_type, min_year, max_km, RTO, color, seating, hub, pitched-car exclusion, free-text preferences); function drives `next_action`, relaxation and 0-car scripts |
| Loan | `get_applicable_loan` (CIBIL × income-slab × employment matrix → LTV % band + ROI band; car-specific AMV when `car_lead_id` passed; no-income-proof category); Type A (eligibility flow) vs Type B (FAQ) classification |
| Scheduling | `schedule_hub_visit` with mandatory read-back; bookable window = today / tomorrow / day-after only; FOMO rebuttal then callback for later dates; `reschedule_hub_visit` in TDC |
| WhatsApp | `send_car_on_whatsapp` (photos/details/links), `send_location_on_whatsapp` (hub location); strict do-not-send list (RC, loan docs, payment instructions) |
| Endings | 3 enforced endings: TD booked / callback captured / notify-when-available |
| Rebuttals | price objection (3-attempt ladder), competitor mention, stale-listing protection, RTO/RC inter-state transfer flow, sell/exchange flow, home TD deflection, token (₹5k refundable, 3 days), zero-DP nuance, voicemail detection, silence handling |
| Persona | Male advisor आर्यन; 2–3 sentence hard cap; numbers in words; anti-robot rules; SSML pacing |

---

## 4. Competitor Bot — Observed Capability Map

| Capability | Evidence | Do we have it? |
|---|---|---|
| Last-call-context greeting ("पिछली बार Fronx के बारे में बात हुई थी") | T1, T3, T7 | ✅ `last_call_summary` greeting |
| Broken-transaction greeting ("Alto K10 के लिए टोकन पेमेंट ट्राय किया") | T2, T8 | ✅ `broken_greeting` |
| Model switch + instant filtered lookup (Fronx→Punch automatic petrol: 1 option, ₹6.32L) | T1 | ✅ via `get_cars...` |
| Hub-level availability + booking status ("अभी अवेलेबल है, बुक नहीं हुई है", "Circle Pare hub पर") | T1 | ⚠️ partial — we expose hub of a car, but no scripted answer for "क्या ये बुक हो गई?" / "कब तक रहेगी?" |
| Token/booking-process explanation (refundable token, pay later, loan option) | T1, T5 | ✅ scripted |
| Zero-down-payment nuance (profile-dependent, no guarantee) | T1 | ✅ scripted |
| Loan eligibility flow (employment → CIBIL → income → estimate) | T1, T2, T3, T5, T6 | ✅ `get_applicable_loan` |
| **Loan amount in ₹ + car-specific re-quote** ("दो लाख से तीन लाख तक", re-quoted for the automatic Kwid) | T2 | ⚠️ only when car finalized (AMV); generic flow speaks LTV % |
| **Down-payment amount in ₹** ("करीब 40 से 45 हज़ार") | T3, T6 | ❌ generic "around twenty percent" only |
| **EMI estimate** ("दो लाख का loan, तीन साल → EMI पांच से छह हज़ार") | T6 | ❌ explicitly forbidden in our NEVER_DO |
| No-income-proof / jobless handling (higher ROI warning, still helps) | T5 | ✅ `no_income_proof` category |
| Unknown-CIBIL handling (proceeds with estimate) | T6 | ✅ `Don't know` band |
| **Cross-city / pan-India search** (Jaipur lead → "all Delhi" Thar search; Mumbai Ertiga search) | T4, T7 | ⚠️ city param + RTO relax exists; no explicit "search any city / all India" behavior |
| **Variant-level inventory** (MX1 vs LX Hard Top Petrol MT 4WD; 3-door vs 5-door Roxx) | T4 | ⚠️ `variant` only surfaces in details; not a search filter |
| Notify-when-available commitment | T4 | ✅ Ending 3 |
| Full car-detail readout (year, fuel, transmission, color, owner, km, insurance type + validity) | T2, T5, T6 | ✅ `get_car_details` flow |
| Honest mismatch disclosure (asked 10k km, available has 29k km) | T2 | ⚠️ not scripted; depends on model behavior |
| Inventory **count + price-range summaries** ("छह option हैं", "₹4.24L से ₹7.20L तक") | T2, T7 | ❌ we forbid speaking car counts (deliberate policy difference) |
| Preference-relaxation ladder (7-seater→5-seater; automatic→manual; fuel relax; budget stretch) | T7, T8 | ✅ function-driven relaxation |
| **Hub *visit* booking (browse, not TD)** with time window ("Sunday 10–11 के बीच") | T3 | ❌ our flow always converts to a car-specific TD slot |
| **Far-date booking** (Sunday / 8th of month, beyond day-after-tomorrow) | T3, T5 | ❌ we restrict to a 3-day window, then FOMO → callback |
| TD slot negotiation (day → time → confirm read-back) | T1, T5 | ✅ Section 9 + 9.1 |
| Delivery-timeline FAQ ("usually 2–3 दिन में") | T5 | ❌ not in prompt |
| **Taxi/commercial guidance** (buy OK; taxi number = local RTO process; hub will guide) | T5 | ❌ we *refuse* commercial/taxi outright |
| Condition/inspection trust pitch (200-point/inspection, all-inclusive price, no hidden charges) | T5, T6, T7 | ✅ scripted |
| **Sell-flow price-dissatisfaction escalation** (procurement-team callback) | T8 | ⚠️ sell flow exists, but no scripted procurement-callback branch for "valuation मिली पर satisfied नहीं" |
| Callback scheduling with time ("शाम पांच के बाद") | T5, T8 | ✅ Ending 2 |
| Calling-window preference capture ("सुबह 8 से रात 8 के बीच कभी भी") | T6 | ⚠️ not explicitly modeled |
| Silence re-engagement ("Are you still there?") | T2, T7 | ✅ silence prompts (count 3, dynamic) |
| SUV-vs-XUV disambiguation | T4, T8 | ⚠️ not scripted (we have a make/model universe validation instead) |
| WhatsApp sending | T5/T6 **refused**, T7 **falsely promised** | ✅ **we actually execute it** — key differentiator |

---

## 5. Competitor Weaknesses → Our Talking Points

| # | Weakness (evidence) | Why it matters / our advantage |
|---|---|---|
| 1 | **Cannot send WhatsApp** — "अभी मैं WhatsApp पर details भेजने में directly help नहीं कर सकता" (T5); refusal directly killed the T6 lead ("नहीं डाल सकते हो तो बंद करो"). In T7 it *promised* photos anyway → broken promise / hallucinated capability, then looped. | We execute `send_car_on_whatsapp` + `send_location_on_whatsapp` in-call and continue the flow. Demonstrable lead-save vs T6. |
| 2 | **Prompt leakage** — "SUV और XUV का अक्सर *transcript* में confusion हो जाता" (T4). | Customer-visible internals; trust-breaking. Our prompts forbid revealing internal mechanics. |
| 3 | **No ending discipline** — T2 ends on customer "no" with no callback; T6 ends with no callback despite "बाद में बात करूंगा"; T7 drifts into repetition with no concrete follow-up time. | Our 3-ending rule guarantees a next action on every call → measurably better re-contact rates. |
| 4 | **Budget never collected** before pitching ₹10L Hector / Octavia to a ~₹6L Punch lead (T8). | Our mandatory preference collection (budget, model, transmission, fuel, year) prevents wasted pitches. |
| 5 | **Factual errors** — Skoda Octavia presented as a petrol-automatic **SUV** (T8); both bots constrained to "SUV body type" options that included a sedan. | Our pitch data is function-fed (pre-formatted price/km/year), reducing hallucinated attributes. |
| 6 | **Mismatch pitching without disclosure** — 1,10,000 km Kwid pitched to a customer who asked "कम चली हुई" (T6); mileage only surfaced when reading details. | Our `additional_user_preferences` + rejection-reason loop is designed to respect stated constraints. |
| 7 | **Closing-loop repetition** — T7: same photo/follow-up pitch repeated 4–5 turns + 2× "Are you still there?"; T5: closing fired twice; T1: closed while the customer asked a final question ("इसमें ali bill आएगी या नहीं?"). | Our anti-repetition + "क्या मैं आपकी कोई और help कर सकता हूँ?" gate before disconnect. |
| 8 | **Compliance-risky loan promises** — quotes EMI amounts and ₹ figures conversationally (T6 EMI "पांच से छह हज़ार"). | Our NEVER_DO forbids promising specific EMI/approvals; we quote bands with "indicative estimate" framing via a controlled matrix. Position this as compliance-safe. |
| 9 | **Repetitive profile questions** — asked salaried/self-employed twice in a row (T3). | Our one-question-at-a-time + reconfirm-once rules. |

---

## 6. Gaps in Our Bot → Prioritized Recommendations

### P0 — direct revenue impact

1. **Add down-payment ₹ estimate to the loan flow.**
   `get_applicable_loan` already returns LTV bands; when a car is in context, also compute and speak `price − max_ltv%` → "down payment लगभग X से Y के बीच" (T3/T6 show customers ask this constantly). Keep "indicative estimate" framing.
2. **Add a compliant EMI *range* capability.**
   Customers ask EMI directly (T6). Today we deflect. Compute an indicative EMI band from (loan band × ROI band × default 5-yr tenure) inside the function — spoken as a range with disclaimer — instead of refusing. Keeps NEVER_DO ("never promise specific EMI") intact since the function, not the LLM, produces the band.
3. **Far-date booking fallback.**
   Competitor happily books Sunday/8th (T3, T5). We FOMO then force a callback. Recommend: keep FOMO for >D+2, but if the customer insists, *book the far slot* (or auto-create a callback on date−1 with the slot pre-noted) rather than leaving only a callback.
4. **Hub-visit (browse) booking mode.**
   T3 customer: "गाड़ी वहां आकर देख सकता हूँ" with a 10–11 AM *window*. Our flow forces a car-specific TD at an exact time. Add a "hub visit" booking variant that accepts a time window and no locked car.

### P1 — coverage gaps

5. **Cross-city search intent.** Support "कहीं भी हो / all Delhi / Mumbai में दिखाओ" explicitly: relax `city` and tell the model when to search other cities or pan-India (T4, T7). Today only RTO-preference relaxation is scripted.
6. **Variant-aware search.** Allow variant keywords (MX1, LX, ZXi, 5-door) in `additional_user_preferences` to be matched/filtered, and let the bot say which *variants* are available when the exact one isn't (T4 did this well).
7. **New FAQ blocks:** (a) delivery timeline ("payment और documents ready हों तो usually 2–3 दिन"); (b) "क्या ये car बुक हो चुकी है / कब तक available रहेगी?" → availability + soft urgency; (c) calling-window preference capture ("X से Y बजे के बीच ही call करना") → store as call-preference metadata.
8. **Taxi/commercial stance — confirm with business.** We refuse outright; competitor guides (buy OK, taxi registration = customer's local RTO process, hub will explain) and converted the lead into a callback (T5). If Spinny policy permits private-registration sales regardless of intended use, soften our refusal to competitor-style guidance.
9. **Sell-flow escalation branch.** Add: if valuation received but customer unsatisfied → offer procurement-team callback with date/time capture (T8 handled this; our sell flow only covers pre-inspection states).
10. **Honest mismatch disclosure rule.** When the closest available car violates a stated constraint (km, year), proactively flag the delta in the pitch ("आपने 10 हज़ार km मांगी थी, ये 29 हज़ार चली है — फिर भी देखना चाहेंगे?") as T2 did. Builds trust and pre-empts the T6 failure mode.

### P2 — config hygiene (issues found in our own JSON)

11. **Gender inconsistency inside scripted lines.** The male-agent rule is contradicted by feminine forms hard-coded in `sql`/`sql_followup` prompts: "समझ गई", "एक सेकंड, आपके लिए अच्छे options देखती हूँ", "एक और कार दिखाती हूँ", "मैं ... book कर देती हूँ", "मैं suggest करूँगी", and the stale-listing line "मैं आपको उसी जैसी कार दिखाती हूँ". These exact-script lines will be spoken verbatim with the wrong gender. Fix all to masculine.
12. **Agent-name drift.** Main prompt: "You are आर्यन"; capability prompt example greeting also uses आर्यन, but the role line in `sql_followup` says "You are aryan" and one main-prompt section says "She is helping me choose properly" (feminine framing left over from a female persona).
13. **Referenced-but-undefined functions.** Prompts instruct calls to `get_number_of_cars_in_a_city`, `get_car_details`, `schedule_hub_visit`, `send_car_on_whatsapp`, `send_location_on_whatsapp`, `mark_callback`, `reschedule_hub_visit`, `switch_capability`, but the config's function list only defines `get_cars_according_to_user_specifications` and `get_applicable_loan` as in-call functions. If the rest are injected at runtime this is fine — verify each is actually registered, otherwise the model will narrate phantom actions (the competitor's T7 WhatsApp hallucination shows exactly how this fails).
14. **Duplicate/garbled numbered rules.** `sql` capability instructions jump 17→19→20→…24 with near-duplicates of snippet rules ("Always confirm customer city…" appears twice; rule 20 truncates: "before asking to schedule f."). Tighten to avoid token waste and contradictions.
15. **Priya/आर्यन handoff line.** Main prompt keeps a "Priya maam is on leave" rebuttal — verify this is still wanted under the male persona.

---

## 7. Deliberate Policy Differences (keep, but be aware)

| Topic | Competitor | Us | Verdict |
|---|---|---|---|
| Speaking car counts / price ranges ("छह option हैं") | Yes | Forbidden | Keep ours if business mandates; but consider allowing *price-range* summaries ("इस budget में options 3.3 से 3.7 लाख के बीच हैं") which T7 used effectively without exact counts. |
| EMI quoting | Free-form by LLM | Forbidden | Move to function-computed band (Rec #2) — best of both. |
| FOMO/urgency | Light, natural | Scripted FOMO at several points | Ours is fine; ensure it never blocks a willing far-date booker (Rec #3). |
| WhatsApp | Cannot send | Can send | Our differentiator — lead every demo with it. |

---

## 8. Appendix — Transcript-by-Transcript Notes

**T1 (Fronx→Punch, TD + zero-DP loan):** Good context greeting, instant model-switch lookup, hub-level availability, refundable-token script, zero-DP nuance, loan estimate (₹4–5L @ 12.5–14%), TD confirm with read-back. *Flaws:* closed while customer asked a final bill question; loan flow skipped explicit CIBIL number (accepted "score बढ़िया है").

**T2 (Alto K10 token → loan → Kwid):** Broken-transaction greeting; clean 3-step loan flow (salaried → CIBIL 750+ → ₹35k → ₹2–3L @ 13–14.5%); full Kwid detail readout incl. insurance validity; honest 10k-vs-29k km mismatch disclosure; spoke car counts ("छह option"); re-quoted loan for the specific automatic Kwid. *Flaws:* call ends on "no" with **no callback captured**.

**T3 (Kwid→i10 → loan with DP → Sunday hub visit):** DP amount quoted (₹40–45k); booked a **hub visit** (not TD) on the 8th with a 10–11 AM **window**; natural urgency line. *Flaws:* asked employment type twice; "interested नहीं" misread initially.

**T4 (Thar Roxx MX1):** Variant-level truth-telling (MX1 absent; LX 3-door present), pan-India check on request, notify-when-available close. *Flaws:* **leaked "transcript" prompt language** to the customer mid-call.

**T5 (Baleno TD + jobless/taxi loan + callback):** Inspection-trust answer with full specs + all-inclusive price; Sunday 6:30 PM TD booked; delivery timeline answer; graceful no-income-proof handling; taxi/RTO conversion guidance; callback at "5 बजे के बाद". *Flaws:* **WhatsApp refusal**; double closing line; talked over the customer repeatedly.

**T6 (₹2.5–3L budget, मज़दूर customer):** EMI math on the fly (₹2L/3yr → 5–6k); proceeded with unknown CIBIL; constraint search (2020+, first owner, ≤3.5L) → Kwid RXL @3.3L; DP quote 20–25%. *Flaws:* pitched a **1.1 lakh-km car to a low-mileage seeker**; **WhatsApp refusal lost the lead**; no callback captured despite an explicit 8 AM–8 PM calling window being offered by the customer.

**T7 (Ertiga Mumbai):** Cross-city search; relaxation ladder (7→5 seater, auto→manual, fuel); price-range summary (₹4.24–7.20L); Tiago options with prices; interpreted "High city" as ground clearance. *Flaws:* **promised WhatsApp photos it cannot send** (contradicts T5/T6); 5-turn repetitive closing loop with 3× "Are you still there?"; no concrete callback time.

**T8 (Dzire CNG → SUV explore; separate sell-flow call):** CNG availability checks across models; SUV/XUV clarification; family-need framing; sell-flow escalation → procurement callback in the evening. *Flaws:* **never asked budget** before pitching ₹10L cars to a ~₹6L lead; **Octavia mislabeled as SUV**; vague callback time accepted ("शाम को").
