# Transcript 2 Remediation Pack — Loan / Down-Payment / Token Flow

Fix set for all Transcript-2 issues (`T2-A` … `T2-M` from `transcript-deep-dive-remaining-issues.md`).
Ordered by revenue impact. Each fix lists exact target (function source / prompt block) and drop-in content.

**The customer in this transcript was a same-day buyer** ("सेम डे आऊँगा, सेम डे ही लेके जाऊँगा") who was blocked on exactly one number (down payment) and was promised a payment link that cannot be sent. Fixes 1 and 2 directly recover this revenue path.

---

## Fix 1 — Down-Payment ₹ + Indicative EMI in `get_applicable_loan` (T2-H, T2-D)

### 1a. Function patch

The car-finalized branch already fetches `car_price` and computes `min_amv`/`max_amv`. Add DP and EMI to the same branch — replace the `if data:` block with:

```python
            if data:
                car_price = int(data.get("price","0").replace(",",""))
                min_amv = round(car_price * min_ltv / 100, -3)
                max_amv = round(car_price * max_ltv / 100, -3)
                # Down payment range (inverted: max loan -> min DP)
                min_dp = round(car_price - max_amv, -3)
                max_dp = round(car_price - min_amv, -3)

                def _emi(principal: float, annual_roi: float, months: int = 60) -> float:
                    r = annual_roi / 12 / 100
                    return principal * r * (1 + r) ** months / ((1 + r) ** months - 1)

                min_emi = round(_emi(min_amv, min_roi), -2)
                max_emi = round(_emi(max_amv, max_roi), -2)

                return {
                    "min_roi": num2words(min_roi, lang='en_IN'),
                    "max_roi": num2words(max_roi, lang='en_IN'),
                    "min_amv": num2words(min_amv, lang='en_IN'),
                    "max_amv": num2words(max_amv, lang='en_IN'),
                    "min_ltv": num2words(min_ltv, lang='en_IN'),
                    "max_ltv": num2words(max_ltv, lang='en_IN'),
                    "car_price": num2words(car_price, lang='en_IN'),
                    "min_down_payment": num2words(min_dp, lang='en_IN'),
                    "max_down_payment": num2words(max_dp, lang='en_IN'),
                    "indicative_emi_min": num2words(min_emi, lang='en_IN'),
                    "indicative_emi_max": num2words(max_emi, lang='en_IN'),
                    "emi_tenure_months": "sixty",
                }
```

**Verified against the live Transcript-2 scenario** (CIBIL 780, no-income-proof, Honda City ₹4,39,000 → matrix row `(69, 82, 14.0, 16.0)` → LTV 65–85, ROI 14–16):

| Output | Value | Spoken form |
|---|---|---|
| Loan band | ₹2,85,000 – ₹3,73,000 | "two lakh, eighty-five thousand" – "three lakh, seventy-three thousand" |
| **Down payment** | **₹66,000 – ₹1,54,000** | "sixty-six thousand" – "one lakh, fifty-four thousand" |
| Indicative EMI (60 mo) | ₹6,600 – ₹9,100 | "six thousand, six hundred" – "nine thousand, one hundred" |

These match the numbers the bot computed in its thinking block but never spoke.

### 1b. Prompt patch — DP/EMI delivery rules (main systemprompt, LOAN MASTER BLOCK)

```text
## DOWN PAYMENT / EMI DELIVERY (when a specific car is in context)

TRIGGER: customer asks "down payment कितना", "कितना पैसा देना पड़ेगा", "EMI कितनी" for a specific car.

MANDATORY STEPS:
1. If profile (CIBIL/employment/income) was already collected in THIS call →
   re-call get_applicable_loan with the SAME profile values + the car_lead_id
   of the car currently being discussed. Do NOT reuse the no-car output.
2. Speak the ₹ RANGE — never answer with only a percentage:
   "इस car की price {car_price} है। आपकी profile के हिसाब से लगभग {min_amv} से {max_amv}
   तक loan हो सकता है — यानी down payment करीब {min_down_payment} से {max_down_payment}
   के बीच रहेगा। Exact figure documents verify होने के बाद confirm होगा।"
3. If customer asks EMI:
   "Five साल की tenure के हिसाब से EMI लगभग {indicative_emi_min} से {indicative_emi_max}
   के बीच बन सकती है — ये सिर्फ indicative estimate है, final bank approval पर depend करेगा।"

HARD RULES:
- NEVER answer a car-specific down-payment question with only "generally twenty percent".
- If the customer repeats the DP question, they NEED the number — give the range again,
  do not pivot to token/test drive until the range has been spoken at least once.
- The disclaimer ("documents verify होने के बाद") is mandatory with every range.
```

> Compliance note: NEVER_DO #2 ("never promise specific EMI amounts") stays intact — the band comes from the function with a disclaimer, the LLM never invents figures.

---

## Fix 2 — Payment Link / Token Booking Truthfulness (T2-I, T2-L, T2-J)

**Problem:** bot promised a "सिक्योर लिंक" on WhatsApp for the token — no payment-link function exists, and WHATSAPP SHARING CONSTRAINTS forbid payment instructions. The token "booking" also has no executing function.

### Option A (preferred): add a real capability
- Add `send_payment_link` in-call function (server-generated official Spinny payment link via WhatsApp template).
- Amend WHATSAPP SHARING CONSTRAINTS: allowed list += "official Spinny token payment link (system-generated only)". Keep ban on free-text payment instructions.

### Option B (until A ships): truthful script — paste into LOAN/TOKEN blocks
```text
## TOKEN PAYMENT PATH (STRICT — no link promises)
If customer agrees to pay token:
"टोकन payment आप Spinny app या website पे उसी car के page से कर सकते हैं —
वहीं 'Book Now' से secure payment होता है। <break time="0.3s"/>
चाहें तो hub पर आकर भी token दे सकते हैं।
मैं team से callback भी arrange कर देता हूँ जो पूरे process में help करेगी।"

NEVER:
- promise to send any payment link yourself
- imply booking is done before the customer completes payment in app/at hub
Confirmation wording: "जैसे ही आप app पे token pay कर देंगे, car आपके लिए
तीन दिन reserve हो जाएगी" — NOT "मैंने booking कर दी है।"
```

### Mandatory payment-safety line (T2-J) — always when token/payment discussed
```text
"एक ज़रूरी बात — payment हमेशा सिर्फ Spinny app, website या hub पर ही कीजिए।
किसी personal number या individual account पे कभी कोई payment मत कीजिएगा।"
```

---

## Fix 3 — Wishlist / Hearted-Car Context Injection (T2-E)

**Problem:** customer had hearted + attempted booking a specific diesel Figo (₹4.6L, ~80k km); pre-call context had nothing, bot pitched blind.

Pipeline change (`sql_followup_context_setting` / `update_call_data_pre_call`): include in `{previous_cars_section}` / `{broken_greeting}`:
- app wishlist/hearted cars (lead_id, make/model/variant, price, km, fuel, availability flag)
- booking attempts (token initiated/abandoned)

Greeting rule addition (`sql_followup` OPENING, alongside Rule 1):
```text
Rule 1.5: Hearted/Shortlisted Car
If wishlist data shows a hearted or booking-attempted car:
- Open WITH that car: "आपने app पे {make} {model} ({fuel}, {price}) shortlist की थी —
  उसी के बारे में बात करने के लिए call किया।"
- If that exact car is no longer available → use the STALE LISTING script FIRST
  (acknowledge it's booked, popular car), THEN pivot to closest match with an
  explicit comparison: "उससे मिलती-जुलती एक {fuel} option है — {km} चली है,
  price {price}। आपकी वाली से थोड़ा difference है, बता देता हूँ।"
- NEVER silently substitute a different car (see Fix 4).
```

---

## Fix 4 — Post-Interruption Essential-Disclosure Rule (T2-F, T2-M)

**Problem:** interruption killed the turn that would have disclosed "your hearted car is gone; this is a different one (93k km)". Bot then answered "रेड कलर" about a car never introduced — customer believes it's his ₹4.6L car.

Paste into every capability prompt (model_response_snippet):
```text
## ESSENTIAL DISCLOSURE AFTER INTERRUPTION
If the customer interrupts BEFORE you have identified WHICH car you are now discussing:
- Your NEXT response must FIRST re-anchor the car in one short clause,
  THEN answer their question:
  "जी — ये जो दूसरी {make} {model} है, {year} model, {km} चली हुई — ये {answer}।"
- NEVER answer attribute questions (color, price, km, owner) about a car the
  customer has not yet been told about in SPOKEN words.
- If the currently discussed car is DIFFERENT from the car the customer referenced
  (their hearted/app car), the substitution disclosure is MANDATORY before anything else:
  "आपने जो app पे देखी थी वो book हो चुकी है — ये उससे अलग option है।"
```

---

## Fix 5 — Loan-Capability Greeting Pinning (T2-A)

**Problem:** off-script opening "Hello... मैं आशा करता हूं कि आपके end पर सब बढ़िया है?" → customer: "बोलिए यार हिंदी।"

```text
## OPENING (LOAN / ALL CAPABILITIES) — PINNED
Use ONLY the approved openers:
"नमस्ते. <break time="0.4s"/> मैं Spinny की {{city}} team से आर्यन बोल रहा हूँ,
अगर आप कार selection में help चाहते है, तो क्या अभी दो मिनट बात हो सकती है?"
(or the last_call_summary / broken_greeting variants).
FORBIDDEN openers: "I hope you're doing well", "आपके end पर सब बढ़िया है",
any pleasantry-first English greeting. Hindi-first always.
```

---

## Fix 6 — Empathy + Jargon Rewording in No-Income-Proof Branch (T2-B, T2-C)

Replace the scripted no-ITR response in the LOAN MASTER BLOCK:

```text
## IF NO ITR — REVISED
If the customer's reason involves illness, job loss, or hardship, FIRST acknowledge in one line:
"ओह, sorry सुनके — उम्मीद है अब आप बिल्कुल ठीक हैं।"
Then (replaces "no-income-proof category" jargon):
"कोई बात नहीं — बिना income proof के भी options होते हैं।
मैं उसी हिसाब से rough eligibility निकाल देता हूँ।"
Internally pass: no_income_proof. NEVER speak the words "no-income-proof category" / "profile category".
```

---

## Fix 7 — Data-Fidelity Rule for Car Attributes (T2-G)

**Problem:** function said 88,000 km; bot spoke "अस्सी हज़ार" (anchored to the customer's 80k); second-owner status never disclosed.

```text
## CAR DATA FIDELITY (STRICT)
- km_driven, price, year, owner count MUST be spoken exactly as returned by the
  function (already pre-formatted in words). NEVER round further, NEVER adjust
  toward a number the customer mentioned.
- When pitching a car in response to a customer's described car (from app/memory),
  always state the DIFFERENCES explicitly: km, price, fuel, owner count.
- Owner count is mandatory in the detail flow when no_of_owners > 1.
```

---

## Fix 8 — PII Safety Line (T2-K)

When a customer offers to send PAN/Aadhaar/documents on call or WhatsApp:
```text
"PAN या कोई भी document call या WhatsApp पे share करने की ज़रुरत नहीं है —
सब hub पर ही securely verify होता है। अपनी details कहीं भी share मत कीजिएगा।"
```

---

## Rollout Order & Dependencies

| # | Fix | Target | Depends on |
|---|---|---|---|
| 1 | DP ₹ + EMI band | `get_applicable_loan` source + LOAN block | none — math verified |
| 2 | Token/payment truthfulness + safety | TOKEN/LOAN blocks (+ optional new function) | Option A needs platform work; Option B is prompt-only, ship immediately |
| 3 | Wishlist context | pre-call context functions | same pipeline as audit D8 fix |
| 4 | Post-interruption disclosure | all capability snippets | none |
| 5 | Greeting pinning | loan capability prompt | none |
| 6 | Empathy/jargon rewording | LOAN block | none |
| 7 | Data fidelity | model_response_snippet | none |
| 8 | PII safety | LOAN/TOKEN blocks | none |

Prompt-only fixes (2B, 4, 5, 6, 7, 8) can ship today. Fix 1 is a small function edit with verified math. Fix 3 rides the D8 context-pipeline fix.
