"""Advisor-style fallback handling for car search results.

The helpers in this module sit after inventory fetching. They do not call any
external API; instead they explain the result set like a human car advisor:

* exact requested cars within budget are pitched first;
* exact requested cars outside budget provide a starting-price anchor;
* if the requested model is unavailable, segment alternatives are suggested.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping, Sequence


SEGMENT_ALTERNATIVES: Mapping[str, tuple[str, ...]] = {
    "alto": ("kwid", "eon", "i10"),
    "i10": ("alto", "kwid", "eon"),
    "kwid": ("alto", "eon", "redi-go"),
    "wagon r": ("celerio", "grand i10", "tiago"),
    "celerio": ("wagon r", "grand i10", "s-presso"),
    "tiago": ("celerio", "grand i10", "punch"),
    "swift": ("baleno", "i20", "glanza"),
    "baleno": ("swift", "i20", "glanza", "altroz"),
    "i20": ("baleno", "altroz", "swift", "glanza"),
    "altroz": ("baleno", "i20", "swift", "glanza"),
    "glanza": ("baleno", "swift", "altroz"),
    "dzire": ("amaze", "tigor", "xcent"),
    "amaze": ("dzire", "tigor", "xcent"),
    "city": ("verna", "ciaz", "rapid"),
    "verna": ("city", "ciaz", "rapid"),
    "nexon": ("brezza", "venue", "sonet"),
    "brezza": ("nexon", "venue", "sonet"),
    "venue": ("sonet", "nexon", "brezza"),
    "creta": ("seltos", "grand vitara", "kushaq"),
    "seltos": ("creta", "grand vitara", "kushaq"),
    "ertiga": ("xl6", "triber", "carens"),
    "innova": ("alcazar", "carens", "xl6"),
    "fortuner": ("gloster", "endeavour", "tucson"),
}

MODEL_ALIASES: Mapping[str, tuple[str, ...]] = {
    "i20": ("elite i20", "new i20", "i20 active", "i20 n line"),
    "i10": ("grand i10", "grand i10 nios"),
    "alto": ("alto 800", "alto k10"),
    "wagon r": ("wagon r 1.0", "wagon r 1.2", "wagon r stingray"),
    "dzire": ("swift dzire",),
    "ertiga": ("new ertiga",),
    "brezza": ("vitara brezza",),
    "nexon": ("nexon ev",),
    "tiago": ("tiago nrg", "tiago jtp", "tiago ev"),
    "scorpio": ("scorpio n",),
    "innova": ("innova crysta", "innova hycross"),
}


@dataclass(frozen=True)
class CarListing:
    """Normalized car data required for advisor fallback decisions."""

    make: str
    model: str
    price: int
    lead_id: str = ""
    year: int | None = None
    fuel_type: str = ""
    transmission: str = ""


@dataclass(frozen=True)
class AdvisorRecommendation:
    """Decision object that the calling bot can convert into speech."""

    status: str
    message: str
    exact_matches: tuple[CarListing, ...] = ()
    similar_options: tuple[CarListing, ...] = ()
    requested_starting_price: int | None = None


def build_advisor_recommendation(
    inventory: Iterable[CarListing | Mapping[str, object]],
    *,
    requested_model: str,
    max_budget: int | float | None = None,
    max_similar_options: int = 3,
) -> AdvisorRecommendation:
    """Return an advisor-style recommendation for a requested model.

    Args:
        inventory: Search results from the listing API or any equivalent cache.
        requested_model: User-requested model, for example ``"i20"``.
        max_budget: User budget in rupees. If omitted or zero, budget filtering
            is skipped.
        max_similar_options: Maximum number of segment alternatives to return.
    """

    cars = tuple(_coerce_listing(item) for item in inventory)
    requested = _canonical_model(requested_model)
    budget = _normalize_budget(max_budget)

    exact_pool = tuple(car for car in cars if _is_same_model(car.model, requested))
    exact_within_budget = _sort_by_price(
        car for car in exact_pool if budget is None or car.price <= budget
    )

    if exact_within_budget:
        return AdvisorRecommendation(
            status="exact_match",
            message=f"{_display(requested)} options are available in the user's budget.",
            exact_matches=exact_within_budget,
        )

    requested_starting_price = min((car.price for car in exact_pool), default=None)
    similar_options = _find_segment_alternatives(cars, requested, budget, max_similar_options)

    if requested_starting_price is not None:
        if similar_options:
            message = (
                f"{_display(requested)} current budget mein available nahi hai. "
                f"{_display(requested)} ka starting price {_format_price(requested_starting_price)} hai. "
                f"Similar options mein {_join_models(similar_options)} available hain."
            )
            status = "over_budget_with_similar"
        else:
            message = (
                f"{_display(requested)} current budget mein available nahi hai. "
                f"{_display(requested)} ka starting price {_format_price(requested_starting_price)} hai."
            )
            status = "over_budget"
        return AdvisorRecommendation(
            status=status,
            message=message,
            similar_options=similar_options,
            requested_starting_price=requested_starting_price,
        )

    if similar_options:
        return AdvisorRecommendation(
            status="unavailable_with_similar",
            message=(
                f"Currently {_display(requested)} available nahi hai. "
                f"Similar options mein {_join_models(similar_options)} available hain."
            ),
            similar_options=similar_options,
        )

    return AdvisorRecommendation(
        status="unavailable",
        message=(
            f"Currently {_display(requested)} available nahi hai, aur close segment "
            "alternatives bhi current inventory mein available nahi hain."
        ),
    )


def _coerce_listing(item: CarListing | Mapping[str, object]) -> CarListing:
    if isinstance(item, CarListing):
        return item
    return CarListing(
        make=str(item.get("make", "")),
        model=str(item.get("model", "")),
        price=int(float(item.get("price", 0) or 0)),
        lead_id=str(item.get("lead_id", item.get("car_lead_id", item.get("id", "")))),
        year=_optional_int(item.get("year", item.get("make_year"))),
        fuel_type=str(item.get("fuel_type", "")),
        transmission=str(item.get("transmission", "")),
    )


def _find_segment_alternatives(
    cars: Sequence[CarListing],
    requested: str,
    budget: int | None,
    max_options: int,
) -> tuple[CarListing, ...]:
    alternatives = SEGMENT_ALTERNATIVES.get(requested, ())
    if not alternatives:
        return ()

    best_by_model: dict[str, CarListing] = {}
    for car in _sort_by_price(cars):
        model = _canonical_model(car.model)
        if model not in alternatives:
            continue
        if budget is not None and car.price > budget:
            continue
        best_by_model.setdefault(model, car)

    ordered = [best_by_model[model] for model in alternatives if model in best_by_model]
    return tuple(ordered[:max_options])


def _sort_by_price(cars: Iterable[CarListing]) -> tuple[CarListing, ...]:
    return tuple(sorted(cars, key=lambda car: car.price))


def _canonical_model(model: str) -> str:
    normalized = _norm(model)
    for canonical, aliases in MODEL_ALIASES.items():
        if normalized == canonical or normalized in aliases:
            return canonical
    return normalized


def _is_same_model(model: str, requested: str) -> bool:
    return _canonical_model(model) == requested


def _normalize_budget(max_budget: int | float | None) -> int | None:
    if not max_budget:
        return None
    budget = float(max_budget)
    if budget < 10000:
        budget *= 100000
    return int(budget)


def _optional_int(value: object) -> int | None:
    try:
        return int(value) if value not in ("", None) else None
    except (TypeError, ValueError):
        return None


def _norm(value: str) -> str:
    return " ".join(str(value).replace("-", " ").casefold().split())


def _display(model: str) -> str:
    if model in {"i10", "i20"}:
        return model
    return model.title()


def _format_price(price: int) -> str:
    rounded_price = int(round(price / 1000) * 1000)
    return _number_to_words_indian(rounded_price)


def _number_to_words_indian(value: int) -> str:
    if value == 0:
        return "zero"

    parts: list[str] = []
    lakh, remainder = divmod(value, 100000)
    thousand, remainder = divmod(remainder, 1000)
    hundred, remainder = divmod(remainder, 100)

    if lakh:
        parts.append(f"{_number_under_1000_to_words(lakh)} lakh")
    if thousand:
        parts.append(f"{_number_under_1000_to_words(thousand)} thousand")
    if hundred:
        parts.append(f"{_number_under_1000_to_words(hundred)} hundred")
    if remainder:
        parts.append(_number_under_100_to_words(remainder))

    return " ".join(parts)


def _number_under_1000_to_words(value: int) -> str:
    hundred, remainder = divmod(value, 100)
    parts: list[str] = []
    if hundred:
        parts.append(f"{_number_under_100_to_words(hundred)} hundred")
    if remainder:
        parts.append(_number_under_100_to_words(remainder))
    return " ".join(parts)


def _number_under_100_to_words(value: int) -> str:
    units = (
        "zero",
        "one",
        "two",
        "three",
        "four",
        "five",
        "six",
        "seven",
        "eight",
        "nine",
        "ten",
        "eleven",
        "twelve",
        "thirteen",
        "fourteen",
        "fifteen",
        "sixteen",
        "seventeen",
        "eighteen",
        "nineteen",
    )
    tens = (
        "",
        "",
        "twenty",
        "thirty",
        "forty",
        "fifty",
        "sixty",
        "seventy",
        "eighty",
        "ninety",
    )
    if value < 20:
        return units[value]
    ten, unit = divmod(value, 10)
    if unit:
        return f"{tens[ten]} {units[unit]}"
    return tens[ten]


def _join_models(cars: Sequence[CarListing]) -> str:
    seen: set[str] = set()
    names: list[str] = []
    for car in cars:
        canonical = _canonical_model(car.model)
        if canonical in seen:
            continue
        seen.add(canonical)
        names.append(_display(canonical))
    return ", ".join(names)
