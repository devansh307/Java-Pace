"""
car_segments.py
===============
Indian used-car segment classification for the voice bot.

Segments:  A1 → A2 → B1 → B2 → C1 → C2 → D1 → D2  (economy → luxury)

Voice-bot actions
-----------------
  PITCH   – Proactively sell.  Lead with price, top 3 features, current offer,
             EMI estimate, and close with a test-drive ask.
  SUGGEST – Mention as an alternative / upgrade only.  Do not hard-sell;
             wait for the customer to express interest before going deeper.

Default PITCH segments  : A2, B1, B2, C1
Default SUGGEST segments: A1, C2, D1, D2

Usage (inside get_cars_according_to_user_specifications)
---------------------------------------------------------
    from car_segments import get_car_segment_info, get_segment_for_budget

    seg_info = get_car_segment_info(
        make=car["make"], model=car["model"], price=car["price"],
        similar_cars_dict=SIMILAR_CARS          # the dict already in the fn
    )
    # seg_info = {
    #   "segment_code":        "C1",
    #   "voice_bot_action":    "PITCH",
    #   "segment_name":        "Compact / Mid SUV",
    #   "segment_description": "...",
    #   "pitch_script_hint":   "...",
    # }
"""

from __future__ import annotations

from typing import Optional

# ---------------------------------------------------------------------------
# 1.  SIMILAR_CARS segment-string  →  A1–D2 code
# ---------------------------------------------------------------------------
SEGMENT_CODE_MAP: dict[str, str] = {
    "Entry Hatchback":    "A1",
    "Budget Hatchback":   "A2",
    "Micro SUV":          "A2",
    "Premium Hatchback":  "A2",
    "Compact Sedan":      "B1",
    "Van":                "B1",
    "Mid Sedan":          "B2",
    "Premium Sedan":      "B2",
    "Compact SUV":        "C1",
    "Mid SUV":            "C1",
    "Utility SUV":        "C1",
    "Full/Lifestyle SUV": "C2",
    "Compact MUV":        "C2",
    "Mid/Premium MUV":    "C2",
    "Premium SUV":        "D1",
    "Full-Size SUV":      "D1",
}

# ---------------------------------------------------------------------------
# 2.  A1–D2  →  voice-bot action
# ---------------------------------------------------------------------------
SEGMENT_VOICE_BOT_ACTION: dict[str, str] = {
    "A1": "SUGGEST",   # very low margin; only pitch if customer insists on cheapest
    "A2": "PITCH",     # high-volume entry hatchback; best for first-time buyers
    "B1": "PITCH",     # compact sedans; popular with small families
    "B2": "PITCH",     # mid sedans; aspirational professionals
    "C1": "PITCH",     # compact/mid SUV; hottest & highest-margin segment in India
    "C2": "SUGGEST",   # 7-seater SUV/MPV; suggest when customer needs more seats
    "D1": "SUGGEST",   # full-size SUV; suggest only for confirmed high-budget leads
    "D2": "SUGGEST",   # luxury (₹50L+); outside Spinny's primary inventory range
}

# ---------------------------------------------------------------------------
# 3.  Human-readable metadata per segment
# ---------------------------------------------------------------------------
SEGMENT_META: dict[str, dict] = {
    "A1": {
        "name":        "Mini / Entry Hatchback",
        "price_range": "₹1.5–3.5 lakh (used)",
        "description": "Sub-3600 mm micro cars. Very low running cost. Target: first-time/student/city-only buyers.",
        "pitch_script_hint": (
            "Mention only if budget is under ₹3.5 lakh or customer explicitly asks for the "
            "most affordable option.  Lead with low EMI and low maintenance cost."
        ),
        "examples": ["Maruti Alto", "Renault Kwid", "Maruti S-Presso"],
    },
    "A2": {
        "name":        "Compact / Premium Hatchback",
        "price_range": "₹3–7 lakh (used)",
        "description": "India's highest-volume segment. Good mileage, modern features, easy to park.",
        "pitch_script_hint": (
            "Lead with mileage, brand resale value, and any sunroof/connected-car feature. "
            "Highlight low EMI (₹X/month). Close with test-drive ask."
        ),
        "examples": ["Maruti Swift", "Maruti Baleno", "Hyundai i20", "Tata Altroz", "Toyota Glanza"],
    },
    "B1": {
        "name":        "Compact Sedan",
        "price_range": "₹4–8 lakh (used)",
        "description": "Sub-4m sedans with boot space. Great family cars at low TCO.",
        "pitch_script_hint": (
            "Pitch the extra boot space and sedan status vs hatchback. "
            "Ideal upsell from A2. Mention AMT/automatic availability for convenience."
        ),
        "examples": ["Maruti Dzire", "Honda Amaze", "Hyundai Aura", "Tata Tigor"],
    },
    "B2": {
        "name":        "Mid Sedan",
        "price_range": "₹6–13 lakh (used)",
        "description": "Feature-rich full-size sedans for professionals and executives.",
        "pitch_script_hint": (
            "Emphasise premium cabin, ADAS features, and strong resale value. "
            "Suggest as a step-up from B1 or an alternative for customers who prefer sedan over SUV."
        ),
        "examples": ["Honda City", "Hyundai Verna", "Maruti Ciaz", "Skoda Slavia", "VW Virtus"],
    },
    "C1": {
        "name":        "Compact / Mid SUV",
        "price_range": "₹7–18 lakh (used)",
        "description": "India's fastest-moving used-car segment. High ground clearance, bold styling, strong resale.",
        "pitch_script_hint": (
            "Lead every SUV conversation here. Pitch sunroof, ADAS, strong resale, and "
            "all-road capability.  Quote EMI and current offer proactively. "
            "Always ask: 'Would you like to book a test drive?'"
        ),
        "examples": ["Hyundai Creta", "Kia Seltos", "Maruti Grand Vitara", "Tata Nexon",
                     "Maruti Brezza", "Kia Sonet", "Hyundai Venue", "Skoda Kushaq"],
    },
    "C2": {
        "name":        "Large SUV / 6–7 Seater MPV",
        "price_range": "₹10–25 lakh (used)",
        "description": "7-seater command-of-road SUVs and premium MPVs for large families.",
        "pitch_script_hint": (
            "Suggest as upgrade only when customer mentions 6–7 seats, large family, "
            "or asks for 'bigger SUV'. Highlight 3rd-row comfort and towing capability."
        ),
        "examples": ["Mahindra XUV700", "Tata Safari", "Hyundai Alcazar",
                     "Toyota Innova Crysta", "Kia Carens", "Mahindra Scorpio-N"],
    },
    "D1": {
        "name":        "Full-Size SUV / Near-Luxury",
        "price_range": "₹18–45 lakh (used)",
        "description": "Genuine 4x4 capability and premium features. High-income segment.",
        "pitch_script_hint": (
            "Pitch only after customer confirms budget > ₹20 lakh or is an identified "
            "high-intent lead. Lead with off-road credentials and resale brand value."
        ),
        "examples": ["Toyota Fortuner", "MG Gloster", "Jeep Meridian", "Isuzu MU-X"],
    },
    "D2": {
        "name":        "Luxury",
        "price_range": "₹30 lakh+ (used)",
        "description": "German / Scandinavian luxury marques. Very niche; outside Spinny's primary range.",
        "pitch_script_hint": (
            "Never cold-pitch. Suggest only to identified HNI customers who explicitly ask "
            "for BMW, Mercedes, Audi, Volvo, or similar."
        ),
        "examples": ["BMW 3/5 Series", "Mercedes C/E-Class", "Audi A4/Q5", "Volvo XC40/XC60"],
    },
}

# ---------------------------------------------------------------------------
# 4.  Budget-based routing  (used-car price in rupees)
#     Returns which segment to PITCH and which to SUGGEST for a given budget.
# ---------------------------------------------------------------------------
_BUDGET_ROUTING: list[dict] = [
    {"max_price":   300_000, "pitch": "A1", "suggest": "A2"},
    {"max_price":   600_000, "pitch": "A2", "suggest": "B1"},
    {"max_price":   900_000, "pitch": "B1", "suggest": "A2"},
    {"max_price": 1_400_000, "pitch": "B2", "suggest": "C1"},
    {"max_price": 2_000_000, "pitch": "C1", "suggest": "B2"},
    {"max_price": 3_000_000, "pitch": "C2", "suggest": "C1"},
    {"max_price": 5_000_000, "pitch": "D1", "suggest": "C2"},
    {"max_price": float("inf"), "pitch": "D2", "suggest": "D1"},
]


# ---------------------------------------------------------------------------
# 5.  Internal helpers
# ---------------------------------------------------------------------------

def _segment_from_price(price_rupees: float) -> str:
    """Fallback: infer segment purely from the car's listed price."""
    thresholds = [
        (300_000,   "A1"),
        (600_000,   "A2"),
        (900_000,   "B1"),
        (1_400_000, "B2"),
        (2_000_000, "C1"),
        (3_000_000, "C2"),
        (5_000_000, "D1"),
    ]
    for limit, code in thresholds:
        if price_rupees < limit:
            return code
    return "D2"


# ---------------------------------------------------------------------------
# 6.  Public API
# ---------------------------------------------------------------------------

def get_car_segment_info(
    make: str,
    model: str,
    price: float,
    similar_cars_dict: Optional[dict] = None,
) -> dict:
    """
    Classify a single car into A1–D2 and return voice-bot guidance.

    Parameters
    ----------
    make : str
        Car make as returned by the Spinny API (e.g. "Hyundai").
    model : str
        Car model as returned by the Spinny API (e.g. "Creta").
    price : float
        Listed price in rupees.
    similar_cars_dict : dict, optional
        Pass the ``SIMILAR_CARS`` dict from inside the function so the lookup
        can use it directly.  If None, falls back to price-only classification.

    Returns
    -------
    dict with keys:
        segment_code      – "A1" … "D2"
        voice_bot_action  – "PITCH" | "SUGGEST"
        segment_name      – human-readable segment name
        segment_description
        pitch_script_hint – guidance for the voice bot script
        examples          – sample cars in that segment
    """
    seg_code: Optional[str] = None

    if similar_cars_dict:
        # Exact key match first
        key = f"{make.strip().title()} {model.strip().title()}"
        row = similar_cars_dict.get(key)

        # Fuzzy fallback — importlocally to avoid hard dep if rapidfuzz absent
        if not row:
            try:
                from rapidfuzz import process, fuzz  # already imported in callers
                match = process.extractOne(
                    key, similar_cars_dict.keys(),
                    scorer=fuzz.WRatio, score_cutoff=72,
                )
                if match:
                    row = similar_cars_dict[match[0]]
            except ImportError:
                pass

        if row:
            seg_code = SEGMENT_CODE_MAP.get(row.get("Segment", ""))

    if not seg_code:
        seg_code = _segment_from_price(price)

    meta = SEGMENT_META[seg_code]
    return {
        "segment_code":        seg_code,
        "voice_bot_action":    SEGMENT_VOICE_BOT_ACTION[seg_code],
        "segment_name":        meta["name"],
        "segment_description": meta["description"],
        "pitch_script_hint":   meta["pitch_script_hint"],
        "examples":            meta["examples"],
    }


def get_segment_for_budget(budget_rupees: float) -> dict:
    """
    Given a customer's budget, return the recommended PITCH and SUGGEST segments.

    Example
    -------
        get_segment_for_budget(1_200_000)
        # → {"pitch_segment": "B2", "suggest_segment": "C1", ...}
    """
    for route in _BUDGET_ROUTING:
        if budget_rupees <= route["max_price"]:
            pitch, suggest = route["pitch"], route["suggest"]
            return {
                "pitch_segment":        pitch,
                "suggest_segment":      suggest,
                "pitch_name":           SEGMENT_META[pitch]["name"],
                "suggest_name":         SEGMENT_META[suggest]["name"],
                "pitch_description":    SEGMENT_META[pitch]["description"],
                "suggest_description":  SEGMENT_META[suggest]["description"],
                "pitch_script_hint":    SEGMENT_META[pitch]["pitch_script_hint"],
            }
    # Should never reach here given float("inf") in the last route
    return get_segment_for_budget(5_000_000)


def build_pitch_instruction(car: dict) -> str:
    """
    Returns a [SYSTEM INSTRUCTION] string for the voice bot for a single car.

    Parameters
    ----------
    car : dict
        A single item from the ``data`` list returned by ``return_cars``.
        Must already have ``segment_code`` and ``voice_bot_action`` keys
        (added by the integration patch).

    Returns
    -------
    str  – ready to inject into the LLM prompt / next_action field.
    """
    action = car.get("voice_bot_action", "SUGGEST")
    seg    = car.get("segment_code", "")
    make   = car.get("make", "")
    model  = car.get("model", "")
    price  = car.get("price", "")
    hint   = SEGMENT_META.get(seg, {}).get("pitch_script_hint", "")

    if action == "PITCH":
        return (
            f"[SYSTEM INSTRUCTION — DO NOT READ ALOUD] "
            f"PITCH this car: {make} {model} ({seg} segment) priced at {price}. "
            f"{hint}"
        )
    return (
        f"[SYSTEM INSTRUCTION — DO NOT READ ALOUD] "
        f"SUGGEST this car as an option only: {make} {model} ({seg} segment) priced at {price}. "
        f"Do not hard-sell. Mention briefly and wait for customer interest. {hint}"
    )
