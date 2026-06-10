# Production Call Audit — SQL Bot, 10 June 2026 (15 calls, Jaipur)

Companion to `competitor-analysis-sql-bot.md`. Source: `SQL_Issues_-_Sheet9 (1).csv` — 15 transcripts of today's live calls by आर्यन.

**Headline:** today's calls surface **production-stability defects that outrank competitor-parity features**. Only 1 of 15 calls (Call 15) ended with a clean, rule-compliant outcome (WhatsApp sent + callback at a confirmed time). The single biggest defect — raw `<thinking>` blocks leaking into responses — appears in **7 of 15 calls** and destroyed at least one call outright (Call 12).

---

## 1. Call-by-Call Outcomes

| # | Lead | Scenario | Outcome | Key defects |
|---|---|---|---|---|
| 1 | 24031786 | Exchange Alto 800 → Swift, wants CNG | No ending — cut mid-clarification | 3 questions stacked in opening; pitched before fuel pref collected (CNG surprise after TD push); no callback |
| 2 | 24024175 | Brezza; customer "अभी जा ही रहा हूँ वहाँ देखने" | **Hot lead dropped** — "Take care!" | Customer going to hub *today*; no visit booking, no RM assignment, no time capture |
| 3 | 24037512 | Tiago details + WhatsApp | No ending | `get_car_details` failure exposed ("details निकालने में दिक्कत"); `send_car_on_whatsapp` failure exposed after claiming send; no recovery/callback |
| 4 | 23720853 | Kwid token-broken; wants Sunday visit; trust objection | Saturday reminder callback ✅ | **Verbatim policy leak**: "booking window में सिर्फ आज, कल या परसो के slots" ; 4–6-sentence brochure answers to review concerns (cap is 2–3) |
| 5 | 23577533 | Budget browser | WhatsApp claimed sent; **no callback** | **Budget hallucinated** from garbled "तो। भाई।" → "दो लाख के आसपास, सही समझा?"; pitched 2013/2014 first, customer wanted 2018/19 |
| 6 | 23832545 | Xcent re-engage | Sunday callback ✅ (time self-picked) | Asked "comfort या mileage?" then ignored the answer (decorative question); picked "दोपहर" without asking |
| 7 | 24036232 | Sell-only lead | App + procurement redirect ✅ | **`<thinking>` leaked** into every turn |
| 8 | 23856200 | Brezza/Venue, bad audio | Truncated during function call | — (audio chaos; can't judge) |
| 9 | 24034375 | Silent/side-talk caller | Lost | `<thinking>` leaked; **hallucinated "दिव्या मैम छुट्टी पर हैं"** (Priya rule generalized to a name overheard in a side conversation); identical silence prompt repeated 3× |
| 10 | 24026555 | "3 लाख, पूरी loan चाहिए" | Truncated mid-loan-flow | `<thinking>` leaked; "पूरी loan" (zero-DP intent) not addressed |
| 11 | 24028241 | ₹2.5–3L, Grand i10 | Location WhatsApp sent ✅; but customer's "आके देखते हैं ऑफिस में" → no visit/callback capture | **Spoke car count "दस अच्छी कार्स"** (NEVER_DO #13 breach); pitched 2013 model first → "बहुत पुरानी" |
| 12 | 24017535 | Confused/garbled caller | **Call lost** — customer repeatedly begging "मेरी बात सुनो" | `<thinking>` leaked massively incl. duplicated paragraphs and a malformed merge of thinking + speech; bot effectively unresponsive |
| 13 | 24031786 (again) | Same-day re-call of Call 1 | Filler loop, no ending | **Zero context carry-over from Call 1** (asked budget fresh; no Swift/CNG/exchange memory); greeting repeated twice; `</prosody>` tag leaked; `<thinking>` leaked |
| 14 | 23652205 | SUV diesel ≤5L | Truncated | Two near-identical EcoSports pitched; "इस रेट में नहीं आएगी" (budget/availability) misclassified as **price objection** → wrong rebuttal script, 5-sentence brochure; stray `</thinking>` appended to spoken text |
| 15 | 23177786 | ₹2.5L browser | ✅ Best call: 2017 refetch, both cars WhatsApped, 2 PM callback confirmed | 2013/2014 pitched first (again); "तेरा मोटर नहीं चाहिए" (likely "Tata नहीं चाहिए") misread as i10 rejection |

---

## 2. Cross-Cutting Defects (ranked by frequency × impact)

### D1. Reasoning/tag leakage into responses — 7/15 calls (7, 9, 10, 12, 13, 14, 15)
Raw `<thinking>…</thinking>` blocks, duplicated reasoning paragraphs, a malformed thinking+speech merge (Call 12), stray `</thinking>` inside spoken text (Call 14), and orphan `</prosody>` tags (Call 13). The agent runs "V369 – **Gemini** Eleven Labs Male" — Gemini's reasoning is not being stripped before TTS/transcript. Call 12 was lost to this (latency + garbage output while the customer pleaded "मेरी बात सुनो").
**Fix:** platform-level output sanitizer (strip `<thinking>`/unknown tags before TTS), or disable visible reasoning for the primary model; prompt-side band-aid alone will not hold.

### D2. Function-failure exposure & unverified claims — Call 3 (+ Call 5 risk)
`get_car_details` and `send_car_on_whatsapp` failures were narrated to the customer ("दिक्कत आ रही है") *after* the bot had already claimed the send succeeded. WhatsApp delivery is our #1 differentiator vs the competitor — it must be retried silently, verified before claiming success, and have a scripted graceful fallback (callback + manual send by team).

### D3. Ending-discipline breaches — calls 1, 2, 3, 5, 11, 13 (6/15)
Config mandates 3 valid endings; these calls ended with none. Worst case is **Call 2**: customer announced he was *on his way to the hub right now* and the bot closed with "Take care!" — no hub confirmation, no visit logging, no RM assignment (our own script says the phone number at hub gets an RM assigned). Calls 5/11 had explicit "देख के बताता हूँ / आके देखते हैं" hooks with no callback captured.
**Fix:** strengthen the ending gate: treat "जा रहा हूँ / आता हूँ / देख के बताता हूँ" as triggers for visit-capture or callback-capture *before* any closing line is allowed.

### D4. Guardrail breaches already forbidden in the prompt
- Spoke car count: "जयपुर में **दस** अच्छी कार्स अवेलेबल हैं" (Call 11; NEVER_DO #13).
- Opening stacked 3 questions in one turn (Call 1; violates one-question rule + standalone-greeting rule).
- 4–6-sentence brochure-style answers (Calls 4, 14; violates 2–3-sentence hard cap).
**Fix:** these rules exist but aren't enforced — consider moving caps into the response snippet of every capability and adding a post-generation length/count check.

### D5. Far-date scheduling refusal leaks internal policy — Call 4
"अभी Sunday को direct visit के लिए slot book नहीं कर सकता, क्योंकि **booking window** में सिर्फ आज, कल या परसो के slots ही available हैं" — exactly the policy-driven tone the main prompt forbids, and live confirmation of the competitor-gap P0 (competitor books Sunday slots effortlessly — T3/T5). The Saturday-reminder recovery was good but the refusal framing burns trust.

### D6. Stale/oldest-first pitching — calls 5, 11, 15
2013/2014 models were the default first pitch in three calls; customers reacted "बहुत पुरानी" every time, and in two calls volunteered 2017+/2018+ only after rejecting. The competitor leads with newer stock or asks year first.
**Fix:** recency-weighted ordering in `get_cars_according_to_user_specifications` results, or ask year preference before the first pitch when budget < ₹4L (where old stock dominates).

### D7. Misinterpretation cluster
- **Budget hallucination** from garbled audio: "तो। भाई।" → confirmed-as "दो लाख" (Call 5). Require an explicit numeric token before confirming a budget.
- **Objection misclassification**: "इस रेट में नहीं आएगी" = "my budget won't reach this rate" (availability/budget), answered with the *Spinny-price-is-high* rebuttal ladder (Call 14). Needs a budget-vs-price-objection disambiguation rule.
- **Side-conversation as intent**: overheard "अरे दिव्या…" → hallucinated "दिव्या मैम आज छुट्टी पर हैं" by generalizing the Priya rule (Call 9).
- **Decorative discovery**: asked "comfort या mileage?" then pitched the same two Xcents regardless of the answer (Call 6).

### D8. Same-day context loss — Calls 1 → 13 (same lead 24031786)
Call 1 collected: exchange intent, old Alto 800, Swift 2018–2020, CNG/petrol preference. Call 13 (same day, same lead) opened with the default cold greeting and re-asked budget from scratch — `sql_followup` context (`last_call_summary`, `previous_cars_section`, preferences) was not applied. Either capability routing sent it to `sql` or the summary pipeline (`appendSummary`/`update_call_data_pre_call`) hadn't propagated. This is the highest-leverage data bug: re-calls are our core motion and the competitor's context greetings (T1/T2) work reliably.

### D9. Silence-prompt repetition — Calls 9, 13
Identical "हेलो, क्या आप मुझे सुन पा रहे हैं?" 3× in a row (prompt explicitly says rotate repair phrasings); Call 13 also restarted the full scripted greeting twice (NEVER_DO #9).

---

## 3. Re-Prioritized Roadmap (merging competitor analysis + today's audit)

### P0 — production-blocking (fix before feature work)
1. **Strip `<thinking>`/foreign tags from output** (D1) — platform sanitizer before TTS; 7/15 calls affected, 1 call lost.
2. **WhatsApp & details-function reliability** (D2) — silent retry, verify-then-claim, scripted fallback. This protects our #1 competitive differentiator.
3. **Same-day/sql_followup context continuity** (D8) — verify capability routing + summary propagation for re-calls.
4. **Ending-gate hardening** (D3) — visit/callback capture mandatory on "जा रहा हूँ/देख के बताता हूँ/आके देखते हैं" signals; never close a hot lead with "take care".
5. **Far-date booking fallback** (D5 + competitor T3/T5) — keep FOMO, but book far slots or auto-callback date−1 *without* exposing "booking window".

### P1 — revenue & quality
6. Down-payment ₹ estimate + function-computed indicative EMI band in `get_applicable_loan` (competitor T3/T6; Call 10's "पूरी loan चाहिए" shows live demand for funding-percentage answers).
7. Recency-weighted pitch ordering / year-pref-first for low budgets (D6).
8. Guardrail enforcement: car-count ban, one-question opening, 2–3-sentence cap as hard post-checks (D4).
9. Budget-vs-price-objection disambiguation + numeric-required budget confirmation (D7).
10. Hub-visit (browse) booking mode with time windows (competitor T3; Call 2 and Call 11 customers wanted exactly this).
11. Cross-city/pan-India search intent + variant-aware search (competitor T4/T7).
12. New FAQ blocks: delivery timeline, booking status, calling-window capture (competitor T1/T5/T6).

### P2 — hygiene
13. Rotate silence/repair prompts; cap repeats; no greeting restarts (D9).
14. Side-conversation detection; restrict the Priya rule to "Priya" only (D7).
15. Fix feminine forms / persona drift / duplicated rules in prompts (from JSON review).
16. Pitch-pair diversity (avoid two near-identical cars, Call 14).
17. Sell-flow procurement-callback branch for "valuation मिली पर satisfied नहीं" (competitor T8).

---

## 4. Scorecard vs Competitor (evidence now on both sides)

| Dimension | Competitor (8 transcripts) | Us (15 calls today) |
|---|---|---|
| Output cleanliness | 1 prompt-leak (T4) | 7 calls with thinking/tag leakage |
| WhatsApp | Cannot send (lost T6 lead) | Can send — worked in Calls 11, 15; **failed and was exposed in Call 3** |
| Ending discipline | Weak (3/8 no callback) | Weak in practice too (6/15 no valid ending) despite strict config |
| Context on re-call | Reliable (T1, T2) | Broken same-day (Calls 1→13) |
| Far-date scheduling | Books freely | Refuses with policy language (Call 4) |
| Loan depth | ₹ amounts, DP, EMI | Flow starts correctly (Call 10) but truncated; no DP/EMI ₹ |
| Pitch relevance | Mismatch risks (T6 km) | Oldest-first stock pitched (3 calls) |
| Guardrail adherence | n/a (different rules) | Violates own rules (count, stacking, length) |

**Bottom line:** our config is stricter and our toolset is broader than the competitor's, but runtime execution quality (model output hygiene, function reliability, context propagation, ending enforcement) is where we are currently losing winnable calls. Fix P0 items 1–4 before investing in new capabilities.
