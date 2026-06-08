"""
voice_bot_integration.py
========================
Exact changes to make to ``get_cars_according_to_user_specifications``
so that every returned car carries its segment code (A1–D2) and the
voice-bot action (PITCH / SUGGEST).

HOW TO APPLY
------------
The changes are grouped in three numbered "CHANGE" blocks below, each
with a comment showing which existing line to place them after.

You do NOT need this file at runtime; it is a human-readable patch guide.
The actual logic lives in car_segments.py.
"""

# ===========================================================================
# CHANGE 1 — Top-level import (add this to the imports at the very top of the
#             module that contains get_cars_according_to_user_specifications)
# ===========================================================================

from car_segments import (
    get_car_segment_info,
    get_segment_for_budget,
    build_pitch_instruction,
    SEGMENT_VOICE_BOT_ACTION,
    SEGMENT_META,
)


# ===========================================================================
# CHANGE 2 — Segment helpers inside return_cars
#
# LOCATION: paste this block immediately after the closing brace of the
#           SIMILAR_CARS dict (the big dict that ends with 'Toyota Fortuner').
#
# These helpers are defined inside return_cars so they close over
# SIMILAR_CARS without any extra parameter passing.
# ===========================================================================

def _get_seg(make: str, model: str, price: float):
    """
    Returns (segment_code, voice_bot_action) for one car.
    Uses SIMILAR_CARS (in enclosing scope) for model-based lookup,
    falls back to price bands if the model isn't found.
    """
    from car_segments import SEGMENT_CODE_MAP, SEGMENT_VOICE_BOT_ACTION, _segment_from_price

    key = f"{make.strip().title()} {model.strip().title()}"
    row = SIMILAR_CARS.get(key)  # noqa: F821  (SIMILAR_CARS is in enclosing scope)

    if not row:
        match = process.extractOne(  # noqa: F821  (process is in enclosing scope)
            key, SIMILAR_CARS.keys(),
            scorer=fuzz.WRatio,  # noqa: F821
            score_cutoff=72,
        )
        if match:
            row = SIMILAR_CARS[match[0]]

    if row:
        seg = SEGMENT_CODE_MAP.get(row.get("Segment", ""))
        if seg:
            return seg, SEGMENT_VOICE_BOT_ACTION[seg]

    seg = _segment_from_price(price)
    return seg, SEGMENT_VOICE_BOT_ACTION[seg]


# ===========================================================================
# CHANGE 3 — Add segment fields to new_car
#
# LOCATION: inside the  ``for car in ranked_filtered:``  loop, right after
#           the existing ``new_car = { ... }`` dict is built.
#
# Replace the current new_car assignment with the version below (adds two
# new fields at the bottom of the dict and the per-car pitch instruction).
# ===========================================================================

# ── BEFORE (existing code, shown for context only) ──────────────────────
_BEFORE = """
new_car = {
    "car_lead_id":  car.get("id", ""),
    "make_year":    ...,
    "make":         ...,
    "model":        ...,
    # ... all existing fields ...
    "discount_value": ...,
}
"""

# ── AFTER (paste this instead) ──────────────────────────────────────────
_AFTER = """
seg_code, vb_action = _get_seg(
    car.get("make", ""), car.get("model", ""), car.get("price", 0)
)
seg_hint = SEGMENT_META.get(seg_code, {}).get("pitch_script_hint", "")

new_car = {
    "car_lead_id":  car.get("id", ""),
    "make_year":    year_to_words(car.get("registration_year", 0), data.get("default_language", "en")),
    "make":         convert_to_words(car.get("make", "")),
    "model":        convert_to_words(car.get("model", "").replace("Dzire", "डिज़ायर")),
    "variant":      convert_to_words(car.get("variant", "")),
    "km_driven":    mileage,
    "fuel_type":    car.get("fuel_type", ""),
    "body_type":    car.get("body_type", ""),
    "transmission": car.get("transmission", ""),
    "city":         car.get("city", ""),
    "price":        price,
    "perks":        car.get("perks", ""),
    "color":        car.get("color", ""),
    "hub":          hub,
    "hub_id":       car.get("hub_id", ""),
    "rto":          car.get("rto", ""),
    "no_of_owners": car.get("no_of_owners", 0),
    "discount_value": num2words(round(discount_value, -3), lang="en_IN")
                      if discount_value > 0 else "no discount",

    # ── NEW: segment classification ──────────────────────────────────
    "segment_code":     seg_code,
    "voice_bot_action": vb_action,
    "pitch_hint":       seg_hint,
    # ─────────────────────────────────────────────────────────────────
}
"""


# ===========================================================================
# CHANGE 4 (optional) — Segment-aware budget routing
#
# LOCATION: right at the beginning of get_cars_according_to_user_specifications,
#           after the payload is assembled (around the ``payload = {…}`` block).
#
# This adds a top-level ``segment_routing`` key to every response so the
# voice bot knows which segment to prioritise for this customer's budget.
# ===========================================================================

# After building the payload, compute budget-level routing once:
_OPTIONAL_ROUTING = """
# Segment routing for this customer's budget
_budget_rupees = (
    max_price * 100_000 if max_price and max_price < 10_000 else max_price or 0
)
_segment_routing = get_segment_for_budget(_budget_rupees) if _budget_rupees else {}
"""

# Then, in every return statement that contains a ``data`` key, add:
#   "segment_routing": _segment_routing,
#
# Example (CASE 2 / pitch path):
_RETURN_WITH_ROUTING = """
return {
    "next_action": "pitch available cars",
    "segment_routing": _segment_routing,   # ← ADD THIS
    **primary_result,
}
"""


# ===========================================================================
# FULL EXAMPLE OUTPUT
#
# After applying all changes, each car dict in ``data`` will look like:
# ===========================================================================

EXAMPLE_CAR_OUTPUT = {
    "car_lead_id":     "abc123",
    "make_year":       "two thousand twenty two",
    "make":            "Hyundai",
    "model":           "Creta",
    "variant":         "SX Opt Turbo DCT",
    "km_driven":       "thirty thousand",
    "fuel_type":       "petrol",
    "body_type":       "suv",
    "transmission":    "automatic",
    "city":            "mumbai",
    "price":           "fourteen lakh",
    "perks":           "",
    "color":           "white",
    "hub":             "Andheri Hub",
    "hub_id":          42,
    "rto":             "mh",
    "no_of_owners":    1,
    "discount_value":  "no discount",

    # ── NEW fields ──────────────────────────────────────────────────
    "segment_code":     "C1",
    "voice_bot_action": "PITCH",
    "pitch_hint": (
        "Lead every SUV conversation here. Pitch sunroof, ADAS, strong resale, and "
        "all-road capability. Quote EMI and current offer proactively. "
        "Always ask: 'Would you like to book a test drive?'"
    ),
}

EXAMPLE_SEGMENT_ROUTING = {
    "pitch_segment":     "C1",
    "suggest_segment":   "B2",
    "pitch_name":        "Compact / Mid SUV",
    "suggest_name":      "Mid Sedan",
    "pitch_description": "India's fastest-moving used-car segment. ...",
    "suggest_description": "Feature-rich full-size sedans for professionals ...",
    "pitch_script_hint": "Lead every SUV conversation here ...",
}
