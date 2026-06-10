# Deep-Dive: Remaining Unidentified Issues in TDC/Loan Feedback Transcripts

Source: 2 full transcripts behind the 10-June feedback ("नई/पुरानी" confusion; pushy CIBIL ask).
Already-known items (ambiguity gate, CIBIL consent, TD context, `<thinking>` leakage) are excluded — this lists what was NOT yet identified.

---

## Transcript 1 (TDC → car unavailable → sql_followup pitch)

### T1-A. State collision: two contradictory call contexts in back-to-back turns ⚠️ CRITICAL (Now_RESOLVED) (PROMPT UPDATED ABOVE CALL FLOW)
Turn 3: *"आपकी test drive **9 जून पांच बजे** के लिए scheduled थी, पर वो कार available नहीं है, किसी और ने book कर ली"* (car-unavailable script).
Turn 5: *"आपकी test drive **आज** scheduled थी, लेकिन आप hub नहीं आ पाए — सब ठीक है ना?"* (no-show recovery script).
Two different TDC branches fired with two different dates and two different premises. **This collision is very likely the real trigger of the customer's "नई पुरानी?" confusion** — he was trying to figure out which conversation he was in. The ambiguity-gate patch treats the symptom; the state machine must pick exactly one branch (car-unavailable supersedes no-show) and never re-greet.

### T1-B. Phantom-context interleaving (Now_RESOLVED) (PROMPT UPDATED ABOVE CALL FLOW)
After the customer already said "दिखा दो" (show similar cars), the bot ignored that acceptance and jumped to the no-show script. Customer acceptance of a branch must lock the flow.

### T1-C. "Spinny Spinny Park" — hub-name template duplication
Greeting says *"Spinny Spinny Park, Jaipur पे"* — template prepends "Spinny" to a hub name that already starts with "Spinny". String-format bug in the TDC context/template.

### T1-D. `<break time="3.0s"/>` mid-turn — dead air
3 seconds of silence inside the unavailability turn; customer responded "हेलो?" thinking the call dropped. Prompt's own SSML table caps breaks at 0.7s. Add a hard cap (sanitizer-level) on break duration.

### T1-E. No apology/empathy for the lost booking
The customer's *booked* car was given to someone else and the bot delivered it flatly, then pitched. A booked-car loss deserves one empathy line ("Sorry, आपकी booked car... बहुत fast-selling थी") before the pivot. Currently no script exists for "booked TD car sold" — only the generic stale-listing block.

### T1-F. Spoke car count — guardrail breach again
*"...अच्छी condition वाली **चार options** हैं"* (NEVER_DO #13). Second live occurrence (also Call 11 in the production audit). Confirms prompt-only enforcement is failing.

### T1-G. Claimed "चारों cars की photos भेज दी" after verbally pitching only 2
Two cars were never named on the call but were sent on WhatsApp. The customer cannot connect photos to conversation; follow-up call will be harder. Rule needed: send only discussed cars, or name all sent cars ("दो Kwid के अलावा दो और options भी भेजे हैं — X और Y").

### T1-H. Variant name mangling: "Renault Kwid one RXT"
"Kwid 1.0 RXT" → digits-to-words conversion ran *inside the variant name*. Number-formatting must exclude variant/model strings.

### T1-I. Zero pitch diversity + missing pitch fields
Both pitched cars were Renault Kwids; pitch omitted transmission/fuel/km from the standard format.

### T1-J. Original TD never recovered
The call's purpose (a scheduled test drive) ended with neither a replacement TD attempt nor a formal acknowledgment that the old booking is void — only photos + a 2-hour callback. The replacement-TD ask should come after WhatsApp send ("इनमें से जो पसंद आए, उसी slot पे test drive shift कर दूँ?").

---

## Transcript 2 (loan flow → Figo Aspire → Honda City → token)

### T2-A. Off-script corporate/English opening → explicit customer pushback ⚠️
*"Hello. मैं Aryan बोल रहा हूं... मैं आशा करता हूं कि आपके end पर सब बढ़िया है?"* → customer: **"बोलिए यार हिंदी।"**
This greeting exists nowhere in the approved greeting set, violates Hindi-first and anti-telecaller rules, and the customer complained on-call. The loan capability's greeting needs pinning to the standard openers.

### T2-B. Empathy failure on illness disclosure
Customer: *"2 साल से मैं हॉस्पिटल में ही था... कोई काम ही नहीं किया"* → Bot: *"ठीक है"*. The prompt mandates acknowledging feelings; a hospitalization disclosure got a filler. One empathy line required before continuing ("ओह, sorry सुनके — उम्मीद है अब आप बिल्कुल ठीक हैं").

### T2-C. Internal jargon spoken: "नो-इनकम-प्रूफ कैटेगरी"
The scripted line itself leaks internal classification language. Reword the script: *"कोई बात नहीं — बिना income proof के भी options होते हैं, मैं उसी हिसाब से estimate निकाल देता हूँ।"*

### T2-D. LTV percentages are non-actionable — live proof ⚠️
Bot: *"पैंसठ से पचासी परसेंट तक लोन पॉसिबल है"*. Customer's very next decision-relevant statement: *"अभी तो ले पाऊँगा जब मुझे पता लगे **कितना पैसा देना है**"*. Direct evidence for the P1 recommendation (speak ₹ amounts, not LTV %) — for this customer it was the purchase blocker.

### T2-E. Wishlist/booking context missing — pitched blind ⚠️ CRITICAL
Customer had **hearted AND attempted to book** a specific diesel Figo Aspire (₹4.6L, ~80k km) on the app. The bot had no knowledge of it — no broken-transaction greeting, no explored-cars entry — and pitched a generic petrol Figo first. Extension of audit defect D8: app wishlist/heart + booking-attempt data must reach the pre-call context, and this call should have *opened* with that car.

### T2-F. Silent car substitution after interruption ⚠️ CRITICAL
The bot *planned* (in thinking) to disclose "your car may have been booked; closest option is a diesel 93k-km at ₹4.24L" — but the customer interrupted, and **that disclosure was never spoken**. The customer then asked "एंड व्हिच कलर?" and the bot answered "रेड" about a car it never verbally introduced. The customer almost certainly believes he's discussing *his* hearted ₹4.6L/80k-km car. Mental-model mismatch → guaranteed disappointment at the hub.
Rule needed: after an interruption kills a pitch turn, the bot must re-deliver the *essential disclosure* (which car is being discussed) before answering attribute questions.

### T2-G. Factual km misstatement
Honda City data: **88,000 km** ('eighty-eight thousand' in function output). Bot spoke: *"**अस्सी हज़ार** किलोमीटर चली है"* — anchored on the customer's earlier "80,000" figure. Also omitted that the City is a **second-owner** car. Misrepresentation risk at handover.

### T2-H. Down-payment number withheld despite being computed ⚠️ CRITICAL (revenue)
The thinking block computed DP = ₹65,850–₹1,53,650 for the City. The customer asked for the DP amount **four separate times**, declared *"सेम डे आऊँगा, सेम डे ही लेके जाऊँगा"* (ready-to-buy same-day), and explicitly refused to decide without that number. The bot only said *"जनरली ट्वेंटी परसेंट"* and pivoted to token. A compliant range answer existed and was never delivered. This is the strongest live evidence for the P0/P1 DP-₹ recommendation: speak *"रफ estimate के हिसाब से down payment लगभग सत्तर हज़ार से डेढ़ लाख के बीच रहेगा, exact documents verify होने के बाद"*.

### T2-I. Phantom payment-link promise ⚠️ CRITICAL (trust + guardrail conflict)
Bot promised: *"टोकन अमाउंट के लिए सिक्योर लिंक मैं आपको व्हाट्सएप पर भेज देता हूँ"*.
- **No payment-link function exists** in the config (only `send_car_on_whatsapp`, `send_location_on_whatsapp`).
- The WHATSAPP SHARING CONSTRAINTS **explicitly forbid sending payment instructions** on WhatsApp.
Same failure mode we flagged in the competitor (T7 WhatsApp hallucination). If no link arrives, tomorrow's token payment — from a same-day-purchase customer — is lost. Either add a real `send_payment_link` function (and amend the constraint), or script the correct path: token via Spinny app/website or at hub, with a procurement/sales callback to assist.

### T2-J. No payment-security caution
Customer asked: *"किन्हीं के नंबर पे ही डालूँ?"* (should I transfer to someone's personal number?). The bot did not explicitly warn that payments must NEVER go to personal numbers — only the official app/site/hub. One mandatory safety line for any token/payment discussion.

### T2-K. PAN-sharing deflected but not safety-flagged
Customer offered to send his PAN number on chat. Bot correctly said documents aren't needed over the phone, but should add: *"PAN या कोई भी document call या WhatsApp पे share मत कीजिए — सब hub पर ही verify होता है।"*

### T2-L. Token booking promised with no executing function
"टोकन अमाउंट के साथ बुकिंग कर दूँ?" — there is no in-call function to reserve a car against a token. The reservation will not actually exist unless a post-call process picks it up; the customer believes it is done.

### T2-M. Interruption + long thinking = dropped content (systemic)
Twice in this call, a long thinking block was interrupted and the planned spoken content never got delivered (the substitution disclosure in T2-F; the partial response at "मैं ये कह रहा हूँ..."). The output sanitizer fix (P0 #1) also reduces this latency window; additionally, capability prompts need a "resume essential disclosure after interruption" rule.

---

## Updated Priority Injections

| New issue | Goes into | Priority |
|---|---|---|
| T1-A/B TDC state collision (one-branch lock) | TDC state machine / `tdc` prompt | **P0** — likely root cause of feedback #1 |
| T2-I phantom payment link (+ T2-L token booking) | Function gap + WhatsApp constraints | **P0** — broken promise to a buying customer |
| T2-E wishlist/heart context injection | Pre-call context pipeline (with D8) | **P0** — extends context-continuity fix |
| T2-F/M post-interruption disclosure re-delivery | All capability prompts | **P0** |
| T2-H DP ₹ range delivery | `get_applicable_loan` output + loan block | **P0** (upgraded from P1 — blocked a same-day buyer) |
| T1-D break-duration cap, T1-H variant mangling | Output sanitizer / formatter | P1 (bundle with `<thinking>` strip) |
| T1-F car count, T1-G unsent-car claims | Guardrail enforcement | P1 |
| T2-A greeting pinning, T2-B/C empathy & jargon | Loan capability prompt | P1 |
| T2-G data-accuracy (km/owner), T1-E apology line, T1-J TD recovery ask | Prompts | P1 |
| T2-J/K payment & PII safety lines | Prompts (token/loan blocks) | P1 |
| T1-I pitch diversity/fields | Pitch logic | P2 |
