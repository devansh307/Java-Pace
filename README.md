# Java-Pace — Voice Bot Car Segment Engine

## Car Segment Bifurcation (A1 → D2)

Cars are classified into 8 segments so the voice bot knows **which cars to actively pitch** and **which to only suggest**.

---

### Segment Reference Table

| Segment | Name | Used-Car Price Range | Voice Bot Action | When to use |
|---------|------|----------------------|------------------|-------------|
| **A1** | Mini / Entry Hatchback | ₹1.5 – 3.5 lakh | **SUGGEST** | Only if customer insists on cheapest option |
| **A2** | Compact / Premium Hatchback | ₹3 – 7 lakh | **PITCH** | Default for first-time buyers & budget buyers |
| **B1** | Compact Sedan | ₹4 – 8 lakh | **PITCH** | Small families upgrading from hatchback |
| **B2** | Mid Sedan | ₹6 – 13 lakh | **PITCH** | Professionals / executives who prefer sedans |
| **C1** | Compact / Mid SUV | ₹7 – 18 lakh | **PITCH** | Primary pitch — hottest & highest-margin segment |
| **C2** | Large SUV / 7-Seater MPV | ₹10 – 25 lakh | **SUGGEST** | Suggest when customer needs 6–7 seats |
| **D1** | Full-Size SUV / Near-Luxury | ₹18 – 45 lakh | **SUGGEST** | Suggest only for confirmed high-budget leads |
| **D2** | Luxury (BMW, Merc, Audi…) | ₹30 lakh+ | **SUGGEST** | HNI customers only; never cold-pitch |

---

### PITCH vs SUGGEST — What Each Means for the Bot

```
PITCH  →  Proactively sell
           • Lead with model name, price, top 3 features
           • Quote current offer / discount
           • Mention EMI estimate (₹X/month)
           • Close: "Would you like to book a test drive?"

SUGGEST →  Mention as an option only
           • One sentence: "We also have a [Model] at [Price] if you want more space / features."
           • Do NOT quote EMI or offer unprompted
           • Wait for customer to express interest before going deeper
```

---

### Segment-Wise Car Examples

#### A1 — Mini / Entry Hatchback `[SUGGEST]`
> Maruti Alto K10, Maruti S-Presso, Renault Kwid

#### A2 — Compact / Premium Hatchback `[PITCH]`
> Maruti Swift, Maruti Baleno, Hyundai i20, Tata Altroz, Toyota Glanza,
> Hyundai Grand i10 Nios, Hyundai Santro

#### B1 — Compact Sedan `[PITCH]`
> Maruti Dzire, Honda Amaze, Hyundai Aura, Tata Tigor,
> Toyota Etios, Hyundai Xcent

#### B2 — Mid Sedan `[PITCH]`
> Honda City, Hyundai Verna, Maruti Ciaz, Skoda Slavia, VW Virtus,
> Skoda Rapid, VW Vento, Toyota Corolla Altis

#### C1 — Compact / Mid SUV `[PITCH]`
> Hyundai Creta, Kia Seltos, Maruti Grand Vitara, Tata Nexon,
> Maruti Brezza, Kia Sonet, Hyundai Venue, Skoda Kushaq, VW Taigun,
> Honda Elevate, MG Astor, Toyota Urban Cruiser Hyryder,
> Mahindra XUV3XO, Ford EcoSport, Renault Duster, Honda WR-V,
> Nissan Kicks, Maruti Fronx, Tata Curvv, Toyota Urban Cruiser Taisor

#### C2 — Large SUV / 6–7 Seater MPV `[SUGGEST]`
> Mahindra XUV700, Tata Safari, Tata Harrier, Hyundai Alcazar,
> Toyota Innova Crysta / Hycross, Kia Carens, MG Hector,
> Maruti Ertiga, Maruti XL6, Kia Carens, Mahindra Scorpio-N,
> Hyundai Tucson, Mahindra Thar, Mahindra Bolero

#### D1 — Full-Size SUV / Near-Luxury `[SUGGEST]`
> Toyota Fortuner, MG Gloster, Jeep Meridian, Isuzu MU-X,
> VW Tiguan, Skoda Kodiaq, Honda CR-V, Hyundai Santa Fe

#### D2 — Luxury `[SUGGEST]`
> BMW 3/5/X3/X5 Series, Mercedes C/E/GLC-Class, Audi A4/Q5,
> Volvo XC40/XC60/XC90, Jaguar, Land Rover

---

### Classification Logic (two-step)

```
1. Model-based lookup
   ├── Search SIMILAR_CARS dict by "Make Model" (exact, then fuzzy ≥ 72%)
   └── Map the SIMILAR_CARS "Segment" string → A1–D2 via SEGMENT_CODE_MAP

2. Price-based fallback (if model not in SIMILAR_CARS)
   └── Use listed price thresholds (see car_segments.py)
```

---

### Files

| File | Purpose |
|------|---------|
| `car_segments.py` | Standalone module — all constants, `get_car_segment_info()`, `build_pitch_instruction()` |
| `voice_bot_integration.py` | Step-by-step patch guide showing exactly which lines to add/change in `get_cars_according_to_user_specifications` |

---

### Quick Integration (3 changes to the existing function)

#### Step 1 — Import at the top of the module
```python
from car_segments import get_car_segment_info, SEGMENT_META
```

#### Step 2 — Add `_get_seg` helper inside `return_cars` (after the `SIMILAR_CARS` dict)
```python
def _get_seg(make: str, model: str, price: float):
    from car_segments import SEGMENT_CODE_MAP, SEGMENT_VOICE_BOT_ACTION, _segment_from_price
    key = f"{make.strip().title()} {model.strip().title()}"
    row = SIMILAR_CARS.get(key)
    if not row:
        m = process.extractOne(key, SIMILAR_CARS.keys(), scorer=fuzz.WRatio, score_cutoff=72)
        if m:
            row = SIMILAR_CARS[m[0]]
    if row:
        seg = SEGMENT_CODE_MAP.get(row.get("Segment", ""))
        if seg:
            return seg, SEGMENT_VOICE_BOT_ACTION[seg]
    seg = _segment_from_price(price)
    return seg, SEGMENT_VOICE_BOT_ACTION[seg]
```

#### Step 3 — Add segment fields to `new_car` (inside the `for car in ranked_filtered` loop)
```python
seg_code, vb_action = _get_seg(car.get("make", ""), car.get("model", ""), car.get("price", 0))

new_car = {
    # ... all existing fields unchanged ...
    "segment_code":     seg_code,        # "C1"
    "voice_bot_action": vb_action,       # "PITCH" or "SUGGEST"
    "pitch_hint":       SEGMENT_META.get(seg_code, {}).get("pitch_script_hint", ""),
}
```

That's it. The voice bot now receives `segment_code`, `voice_bot_action`, and `pitch_hint`
on every car in the response.
