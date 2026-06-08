async def get_cars_according_to_user_specifications(
	ctx: "RunContext",
	make: str = "",
	model: str = "",
	city: str = "",
	area_or_locality: str = "",
	fuel_type: str = "",
	max_price: float = 0,
	transmission: str = "",
	body_type: str = "",
	min_year: str = "",
	max_km_driven: str = "",
	rto: str = "",
	color: str = "",
	seating_capacity: int = 0,
	hub_id: int = 0,
	pitched_cars_lead_ids: "List[str]" = None,
	additional_user_preferences: "List[str]" = None,
):
	"""
	Get cars according to user specifications.

	Args:
		make: Make of the car (e.g., "honda"). if unspecified, use empty string; if multiple values, separate by comma, without spaces between the items, e.g "hyundai,maruti".
		model: Model of the car (e.g., "Alto", "Tiago"). if unspecified, use empty string; if multiple values, separate by comma, without spaces between the items, e.g "Alto,Tiago".
		city: City of the car in english (e.g., 'mumbai'). if unspecified, use empty string; if multiple values, separate by comma, without spaces between the items, e.g 'mumbai,delhi'. This can only accept these enum values: ['agra','ahmedabad', 'bangalore', 'chandigarh', 'chennai', 'coimbatore', 'delhi', 'delhi-ncr', 'faridabad', 'ghaziabad', 'gurgaon', 'hyderabad', 'jaipur', 'karnal', 'kochi', 'kolkata', 'lucknow', 'mumbai', 'noida', 'pune', 'sonipat', 'ambala', 'kanpur', 'mysuru', 'vizag', 'visakhapatnam']
		area_or_locality: Area or locality of the user (e.g., "andheri west"). if unspecified, use empty string.
		fuel_type: Fuel type of the car (e.g., "petrol", "diesel", "cng", "petrol,cng", "diesel,cng"). if unspecified, use empty string; if multiple values, separate by comma, without spaces between the items, e.g "diesel,cng".
		max_price: Maximum budget of the user in lakhs (example: if maximum budget is 10 lakh, use 10; if maximum budget is पाँच लाख, use 5); if unspecified, use 0. If the user provides a spoken range or a merged number (e.g. "25 30,00,000 की" meaning ₹25‑30 lakhs always take maximum value), interpret it as follows: when the car segment is economy (Alto, Swift, WagonR, Kwid, etc.) or the first two digits are sequential (45, 67, 89…), treat the number as a range and use the higher value (upper bound) for max_price; when the segment is luxury (Mercedes, BMW, Audi, Fortuner, Jeep, etc.) or no range cues are present, treat the figure as an exact budget. Convert any Hindi number words (e.g., पैंतीस लाख) to digits before applying the rule.
		transmission: Transmission type of the car (e.g., "manual", "automatic"). if unspecified, use empty string; if multiple values, separate by comma, without spaces between the items, e.g "manual,automatic".
		body_type: Body type of the car (e.g., "sedan", "hatchback", "suv"). if unspecified, use empty string; if multiple values, separate by comma, without spaces between the items, e.g "sedan,hatchback".
		min_year: Minimum year of the car (e.g., "2020"). if unspecified, use empty string; if multiple values, use smallest year.
		max_km_driven: Maximum km driven of the car (e.g., "10000"). if unspecified, use empty string; if multiple values, use largest km driven.
		rto: rto state code of the car (e.g., "dl" for delhi). if unspecified, use empty string; if multiple values, separate by comma, without spaces between the items, e.g "dl,up". Allowed prefixes for states are [dl, ch, wb, up, ts, tn, rj, pb, mh, mp, ka, kl, hr, gj, ap] only. DONT use any other prefix.
		color: Color of the car (e.g., "red", "white"). if unspecified, use empty string; if multiple values, separate by comma, without spaces between the items, e.g "red,white".
		seating_capacity: Seating capacity of the car (e.g., 5, 7). if unspecified, use 0.
		hub_id: hub_id of the hub where the user wants to see the car. if unspecified, use 0.
		pitched_cars_lead_ids: list of all the car lead ids that have already been pitched to the user. This is used to filter out these cars from the results so that user is not shown the same car again. if unspecified, use empty list.
		additional_user_preferences: list of additional user likes, dislikes,and rejection reasons not covered by other parameters. Store both positive preferences and rejection reasons here so future car pitches can follow them and avoid repeating rejected options. This is used to add these preferences to the response message while returning results. if unspecified, use empty list. eg. ["wants sunroof", "dislikes red color", "rejects cars older than 2020"]
	Each arg should be in lower case.
	"""
	import asyncio
	from datetime import datetime
	from math import radians, sin, cos, asin, sqrt
	import httpx
	import pytz
	from num2words import num2words
	from rapidfuzz import process, fuzz
	from utils.city_wise_hubs import hubs_with_location
	from utils.helpers import (
		add_functions_called,
		convert_to_words,
		get_colors_for_filter,
		get_hub_location,
		get_hubs_as_string,
		get_job_context,
		get_seating_capacity_for_filter,
		iso_to_human,
		year_to_words,
	)

	# ──────────────────────────────────────────────────────────────────────────
	# SEGMENT CODE MAP
	# Maps the 'Segment' values already present in SIMILAR_CARS → a1-d2 codes.
	#
	# Segment codes (Indian used-car market):
	#   a1  Entry Hatchback        Alto, Kwid, Eon               ≤ ₹3.5 L
	#   a2  Budget/Premium Hatch   Swift, Baleno, i20, Wagon R    ₹3–8 L
	#   b1  Compact Sedan / Micro SUV / Compact MUV
	#                              Dzire, Punch, Kiger, Ertiga    ₹5–11 L
	#   b2  Mid Sedan / Compact SUV / Utility SUV
	#                              City, Nexon, Brezza, Venue     ₹8–17 L
	#   c1  Mid SUV / Premium Sedan / Mid-Premium MUV
	#                              Creta, Seltos, Octavia, Innova ₹12–22 L
	#   c2  Full/Lifestyle SUV / Full-Size SUV
	#                              Scorpio, XUV700, Fortuner      ₹15–35 L
	#   d1  Premium SUV            CR-V, Santa Fe, Tucson         ₹25–45 L
	#   d2  Luxury                 Mercedes, BMW, Audi            > ₹40 L
	#
	# Pitch  = bot actively sells, highlights price/EMI/features, tries to close.
	# Suggest = bot mentions passively as an upgrade option only when relevant.
	# ──────────────────────────────────────────────────────────────────────────
	SEGMENT_CODE_MAP = {
		"Entry Hatchback":    "a1",
		"Budget Hatchback":   "a2",
		"Premium Hatchback":  "a2",
		"Van":                "a2",
		"Micro SUV":          "b1",
		"Compact Sedan":      "b1",
		"Compact MUV":        "b1",
		"Mid Sedan":          "b2",
		"Compact SUV":        "b2",
		"Utility SUV":        "b2",
		"Premium Sedan":      "c1",
		"Mid SUV":            "c1",
		"Mid/Premium MUV":    "c1",
		"Full/Lifestyle SUV": "c2",
		"Full-Size SUV":      "c2",
		"Premium SUV":        "d1",
	}

	SEGMENT_VOICE_BOT_ACTION = {
		"a1": "suggest",
		"a2": "pitch",
		"b1": "pitch",
		"b2": "pitch",
		"c1": "pitch",
		"c2": "suggest",
		"d1": "suggest",
		"d2": "suggest",
	}

	# ──────────────────────────────────────────────────────────────────────────
	# SEGMENT HELPERS  (nested async so they live entirely inside this function)
	# ──────────────────────────────────────────────────────────────────────────
	async def split_cars_by_role(cars: list):
		"""Partition cars into pitch vs suggest using each car's segment code."""
		to_pitch, to_suggest = [], []
		for car in cars:
			seg = car.get("segment", "")
			if SEGMENT_VOICE_BOT_ACTION.get(seg) == "suggest":
				to_suggest.append(car)
			else:
				to_pitch.append(car)
		return to_pitch, to_suggest

	async def _segment_from_price_body(price_rupees: float, body_type: str) -> str:
		"""Fallback segment code using price (₹) + body_type from the API."""
		bt = (body_type or "").lower().strip()
		p = price_rupees / 100_000  # lakhs

		if bt == "hatchback":
			return "a1" if p <= 3.5 else "a2"
		if bt == "sedan":
			if p <= 10:  return "b1"
			if p <= 16:  return "b2"
			if p <= 25:  return "c1"
			return "d1"
		if bt in ("suv", "crossover"):
			if p <= 10:  return "b1"
			if p <= 16:  return "b2"
			if p <= 22:  return "c1"
			if p <= 35:  return "c2"
			return "d1"
		if bt in ("muv", "mpv", "minivan"):
			if p <= 12:  return "b1"
			if p <= 22:  return "c1"
			return "c2"
		if p <= 3.5:  return "a1"
		if p <= 6:    return "a2"
		if p <= 10:   return "b1"
		if p <= 16:   return "b2"
		if p <= 22:   return "c1"
		if p <= 35:   return "c2"
		return "d1"

	async def get_car_segment(make: str, model: str, price_rupees: float, body_type: str, similar_cars_dict: dict) -> str:
		"""
		Return segment code (a1-d2) for a single car.
		Priority: exact SIMILAR_CARS match → fuzzy match (≥70) → price+body_type fallback.
		"""
		make_model_str = f"{make} {model}".strip()
		needle = make_model_str.casefold()
		for key, row in similar_cars_dict.items():
			if key.casefold() == needle:
				return SEGMENT_CODE_MAP.get(row.get("Segment", ""), None) or \
					   await _segment_from_price_body(price_rupees, body_type)
		match = process.extractOne(make_model_str, similar_cars_dict.keys(), scorer=fuzz.WRatio, score_cutoff=70)
		if match:
			best_key, _score, _ = match
			code = SEGMENT_CODE_MAP.get(similar_cars_dict[best_key].get("Segment", ""))
			if code:
				return code
		return await _segment_from_price_body(price_rupees, body_type)

	# ──────────────────────────────────────────────────────────────────────────
	# ALMOST_SIMILAR_CAR — variants/aliases of the same car family.
	# When the user requests any entry in a row, we search the API for all
	# entries in that row, then re-rank to bring the originally-requested
	# variant to the front. The 70% fuzzy filter drops unrelated cars that
	# might come back from the broadened API query.
	# ──────────────────────────────────────────────────────────────────────────
	ALMOST_SIMILAR_CAR = [
        ["i20", "Elite i20", "New i20", "i20 Active", "i20 N Line"],
        ["i10", "Grand i10", "Grand i10 Nios"],
        ["Verna", "Fluidic Verna 4S"],
        ["Elantra", "Neo Fluidic Elantra"],
        ["Santro", "New Santro 1.1"],
        ["Creta", "Creta N-Line"],
        ["Alto", "Alto 800", "Alto K10"],
        ["Wagon R", "Wagon R 1.0", "Wagon R 1.2", "Wagon R Stingray"],
        ["Dzire", "Swift Dzire"],
        ["Ertiga", "New Ertiga"],
        ["Vitara Brezza", "Brezza"],
        ["Celerio", "Celerio X"],
        ["Nexon", "Nexon EV"],
        ["Punch", "Punch EV"],
        ["Tiago", "Tiago EV", "Tiago JTP", "Tiago NRG"],
        ["Tigor", "Tigor JTP"],
        ["Scorpio", "Scorpio N"],
        ["Thar", "Thar Roxx"],
        ["KUV100", "KUV100 NXT"],
        ["TUV300", "TUV 300 PLUS"],
        ["XUV 300", "XUV 3XO"],
        ["Etios", "Etios Liva", "Etios Cross", "Platinum Etios"],
        ["Innova", "Innova Crysta", "Innova Hycross"],
        ["Urban Cruiser", "Urban Cruiser Hyryder"],
        ["Figo", "Figo Aspire", "Freestyle"],
        ["Micra", "Micra Active"],
        ["Rapid", "Rapid New"],
        ["Hector", "Hector Plus"],
        ["Discovery", "Discovery Sport"],
        ["GO", "Go Plus"]
    ]

	def _norm(s: str) -> str:
		"""Lowercase, dashes→spaces, collapse whitespace. Used for case-insensitive
        exact-match comparisons of make/model strings."""
		if not s:
			return ""
		return " ".join(str(s).replace("-", " ").lower().split())

	def expand_almost_similar(value: str):
		if not value:
			return None, None
		needle = _norm(value)
		for row in ALMOST_SIMILAR_CAR:
			if needle in [_norm(x) for x in row]:
				api_csv = ",".join(_norm(x).replace(" ", "-") for x in row)
				return api_csv, needle
		return None, None

	if max_price:
		max_price_in_lakhs = max_price * 100000 if max_price < 10000 else max_price
		if max_price_in_lakhs > 5000000:  # 50 lakhs
			return {
				"success": False,
				"message": "Bot should ask the user to repeat their budget, now when user repeats their budget, if the budget provided is within 50 lakh then proceed further with help in car search, if the budget is still above 50 lakhs, say that you are sorry and that you wont be able to help you within this budget range, my senior expert will help you with this, and then end with 'Thankyou Have a nice day.'"
			}

	def get_params(params_1, params_2):
		curr_params = {**params_1, **params_2}
		if curr_params.get("model"):
			curr_params.pop("body_type", None)
		return curr_params

	# ──────────────────────────────────────────────────────────────────────────
	# SIMILAR_CARS — competitor/alternative lookup table.
	# Each entry includes a 'Segment' label that feeds SEGMENT_CODE_MAP.
	# ──────────────────────────────────────────────────────────────────────────
	SIMILAR_CARS = {
        'Maruti Alto': {'Brand': 'Maruti Suzuki', 'Segment': 'Entry Hatchback', 'Status': 'Current', 'Make Option A': 'Hyundai', 'Model Option A': 'i10', 'Make Option B': 'Hyundai', 'Model Option B': 'Eon', 'Make Option C': 'Renault', 'Model Option C': 'Kwid', 'Make Option D': '', 'Model Option D': '', 'Make Option E': '', 'Model Option E': '', 'Make': 'Maruti', 'Model': 'Alto'},
        'Maruti Estilo': {'Brand': 'Maruti Suzuki', 'Segment': 'Entry Hatchback', 'Status': 'Discontinued', 'Make Option A': 'Maruti', 'Model Option A': 'Alto', 'Make Option B': 'Hyundai', 'Model Option B': 'Eon', 'Make Option C': 'Hyundai', 'Model Option C': 'i10', 'Make Option D': '', 'Model Option D': '', 'Make Option E': '', 'Model Option E': '', 'Make': 'Maruti', 'Model': 'Estilo'},
        'Maruti A-Star': {'Brand': 'Maruti Suzuki', 'Segment': 'Entry Hatchback', 'Status': 'Discontinued', 'Make Option A': 'Maruti', 'Model Option A': 'Alto', 'Make Option B': 'Hyundai', 'Model Option B': 'i10', 'Make Option C': 'Hyundai', 'Model Option C': 'Eon', 'Make Option D': '', 'Model Option D': '', 'Make Option E': '', 'Model Option E': '', 'Make': 'Maruti', 'Model': 'A-Star'},
        'Hyundai Eon': {'Brand': 'Hyundai', 'Segment': 'Entry Hatchback', 'Status': 'Discontinued', 'Make Option A': 'Hyundai', 'Model Option A': 'i10', 'Make Option B': 'Maruti', 'Model Option B': 'Alto', 'Make Option C': 'Renault', 'Model Option C': 'Kwid', 'Make Option D': '', 'Model Option D': '', 'Make Option E': '', 'Model Option E': '', 'Make': 'Hyundai', 'Model': 'Eon'},
        'Hyundai i10': {'Brand': 'Hyundai', 'Segment': 'Entry Hatchback', 'Status': 'Discontinued', 'Make Option A': 'Maruti', 'Model Option A': 'Alto', 'Make Option B': 'Hyundai', 'Model Option B': 'Eon', 'Make Option C': 'Renault', 'Model Option C': 'Kwid', 'Make Option D': '', 'Model Option D': '', 'Make Option E': '', 'Model Option E': '', 'Make': 'Hyundai', 'Model': 'i10'},
        'Renault Kwid': {'Brand': 'Renault', 'Segment': 'Entry Hatchback', 'Status': 'Current', 'Make Option A': 'Hyundai', 'Model Option A': 'Eon', 'Make Option B': 'Maruti', 'Model Option B': 'Alto', 'Make Option C': 'Datsun', 'Model Option C': 'Redi-GO', 'Make Option D': '', 'Model Option D': '', 'Make Option E': '', 'Model Option E': '', 'Make': 'Renault', 'Model': 'Kwid'},
        'Datsun Redi-GO': {'Brand': 'Datsun', 'Segment': 'Entry Hatchback', 'Status': 'Discontinued', 'Make Option A': 'Renault', 'Model Option A': 'Kwid', 'Make Option B': 'Maruti', 'Model Option B': 'Alto', 'Make Option C': 'Hyundai', 'Model Option C': 'Eon', 'Make Option D': '', 'Model Option D': '', 'Make Option E': '', 'Model Option E': '', 'Make': 'Datsun', 'Model': 'Redi-GO'},
        'Tata Nano': {'Brand': 'Tata Motors', 'Segment': 'Entry Hatchback', 'Status': 'Discontinued', 'Make Option A': 'Hyundai', 'Model Option A': 'Eon', 'Make Option B': 'Hyundai', 'Model Option B': 'i10', 'Make Option C': 'Maruti', 'Model Option C': 'Alto', 'Make Option D': '', 'Model Option D': '', 'Make Option E': '', 'Model Option E': '', 'Make': 'Tata', 'Model': 'Nano'},
        'Maruti S-Presso': {'Brand': 'Maruti Suzuki', 'Segment': 'Budget Hatchback', 'Status': 'Current', 'Make Option A': 'Maruti', 'Model Option A': 'Celerio', 'Make Option B': 'Maruti', 'Model Option B': 'Wagon R', 'Make Option C': 'Hyundai', 'Model Option C': 'Grand i10', 'Make Option D': '', 'Model Option D': '', 'Make Option E': '', 'Model Option E': '', 'Make': 'Maruti', 'Model': 'S-Presso'},
        'Maruti Wagon R': {'Brand': 'Maruti Suzuki', 'Segment': 'Budget Hatchback', 'Status': 'Current', 'Make Option A': 'Hyundai', 'Model Option A': 'Grand i10', 'Make Option B': 'Maruti', 'Model Option B': 'Celerio', 'Make Option C': 'Maruti', 'Model Option C': 'Ignis', 'Make Option D': '', 'Model Option D': '', 'Make Option E': '', 'Model Option E': '', 'Make': 'Maruti', 'Model': 'Wagon R'},
        'Maruti Celerio': {'Brand': 'Maruti Suzuki', 'Segment': 'Budget Hatchback', 'Status': 'Current', 'Make Option A': 'Maruti', 'Model Option A': 'Wagon R', 'Make Option B': 'Hyundai', 'Model Option B': 'Grand i10', 'Make Option C': 'Maruti', 'Model Option C': 'S-Presso', 'Make Option D': '', 'Model Option D': '', 'Make Option E': '', 'Model Option E': '', 'Make': 'Maruti', 'Model': 'Celerio'},
        'Maruti Ritz': {'Brand': 'Maruti Suzuki', 'Segment': 'Budget Hatchback', 'Status': 'Discontinued', 'Make Option A': 'Maruti', 'Model Option A': 'Celerio', 'Make Option B': 'Maruti', 'Model Option B': 'S-Presso', 'Make Option C': 'Maruti', 'Model Option C': 'Wagon R', 'Make Option D': '', 'Model Option D': '', 'Make Option E': '', 'Model Option E': '', 'Make': 'Maruti', 'Model': 'Ritz'},
        'Tata Tiago': {'Brand': 'Tata Motors', 'Segment': 'Budget Hatchback', 'Status': 'Current', 'Make Option A': 'Maruti', 'Model Option A': 'Celerio', 'Make Option B': 'Hyundai', 'Model Option B': 'Grand i10', 'Make Option C': 'Tata', 'Model Option C': 'Punch', 'Make Option D': '', 'Model Option D': '', 'Make Option E': '', 'Model Option E': '', 'Make': 'Tata', 'Model': 'Tiago'},
        'Hyundai Grand i10': {'Brand': 'Hyundai', 'Segment': 'Budget Hatchback', 'Status': 'Current', 'Make Option A': 'Maruti', 'Model Option A': 'Celerio', 'Make Option B': 'Maruti', 'Model Option B': 'Wagon R', 'Make Option C': 'Tata', 'Model Option C': 'Tiago', 'Make Option D': '', 'Model Option D': '', 'Make Option E': '', 'Model Option E': '', 'Make': 'Hyundai', 'Model': 'Grand i10'},
        'Hyundai Santro': {'Brand': 'Hyundai', 'Segment': 'Budget Hatchback', 'Status': 'Discontinued', 'Make Option A': 'Maruti', 'Model Option A': 'Celerio', 'Make Option B': 'Hyundai', 'Model Option B': 'Grand i10', 'Make Option C': 'Maruti', 'Model Option C': 'Wagon R', 'Make Option D': '', 'Model Option D': '', 'Make Option E': '', 'Model Option E': '', 'Make': 'Hyundai', 'Model': 'Santro'},
        'Chevrolet Beat': {'Brand': 'Chevrolet', 'Segment': 'Budget Hatchback', 'Status': 'Discontinued', 'Make Option A': 'Maruti', 'Model Option A': 'Celerio', 'Make Option B': 'Hyundai', 'Model Option B': 'i10', 'Make Option C': 'Renault', 'Model Option C': 'Kwid', 'Make Option D': '', 'Model Option D': '', 'Make Option E': '', 'Model Option E': '', 'Make': 'Chevrolet', 'Model': 'Beat'},
        'Datsun GO': {'Brand': 'Datsun', 'Segment': 'Budget Hatchback', 'Status': 'Discontinued', 'Make Option A': 'Hyundai', 'Model Option A': 'i10', 'Make Option B': 'Renault', 'Model Option B': 'Kwid', 'Make Option C': 'Datsun', 'Model Option C': 'Redi-GO', 'Make Option D': '', 'Model Option D': '', 'Make Option E': '', 'Model Option E': '', 'Make': 'Datsun', 'Model': 'GO'},
        'Honda Brio': {'Brand': 'Honda', 'Segment': 'Budget Hatchback', 'Status': 'Discontinued', 'Make Option A': 'Hyundai', 'Model Option A': 'Grand i10', 'Make Option B': 'Maruti', 'Model Option B': 'Celerio', 'Make Option C': 'Maruti', 'Model Option C': 'S-Presso', 'Make Option D': '', 'Model Option D': '', 'Make Option E': '', 'Model Option E': '', 'Make': 'Honda', 'Model': 'Brio'},
        'Nissan Micra': {'Brand': 'Nissan', 'Segment': 'Budget Hatchback', 'Status': 'Discontinued', 'Make Option A': 'Tata', 'Model Option A': 'Tiago', 'Make Option B': 'Renault', 'Model Option B': 'Kwid', 'Make Option C': 'Maruti', 'Model Option C': 'Celerio', 'Make Option D': '', 'Model Option D': '', 'Make Option E': '', 'Model Option E': '', 'Make': 'Nissan', 'Model': 'Micra'},
        'Maruti Swift': {'Brand': 'Maruti Suzuki', 'Segment': 'Premium Hatchback', 'Status': 'Current', 'Make Option A': 'Maruti', 'Model Option A': 'Baleno', 'Make Option B': 'Hyundai', 'Model Option B': 'i20', 'Make Option C': 'Toyota', 'Model Option C': 'Glanza', 'Make Option D': '', 'Model Option D': '', 'Make Option E': '', 'Model Option E': '', 'Make': 'Maruti', 'Model': 'Swift'},
        'Maruti Baleno': {'Brand': 'Maruti Suzuki', 'Segment': 'Premium Hatchback', 'Status': 'Current', 'Make Option A': 'Maruti', 'Model Option A': 'Swift', 'Make Option B': 'Hyundai', 'Model Option B': 'i20', 'Make Option C': 'Toyota', 'Model Option C': 'Glanza', 'Make Option D': '', 'Model Option D': '', 'Make Option E': '', 'Model Option E': '', 'Make': 'Maruti', 'Model': 'Baleno'},
        'Hyundai i20': {'Brand': 'Hyundai', 'Segment': 'Premium Hatchback', 'Status': 'Current', 'Make Option A': 'Maruti', 'Model Option A': 'Swift', 'Make Option B': 'Maruti', 'Model Option B': 'Baleno', 'Make Option C': 'Toyota', 'Model Option C': 'Glanza', 'Make Option D': '', 'Model Option D': '', 'Make Option E': '', 'Model Option E': '', 'Make': 'Hyundai', 'Model': 'i20'},
        'Tata Altroz': {'Brand': 'Tata Motors', 'Segment': 'Premium Hatchback', 'Status': 'Current', 'Make Option A': 'Maruti', 'Model Option A': 'Swift', 'Make Option B': 'Hyundai', 'Model Option B': 'i20', 'Make Option C': 'Toyota', 'Model Option C': 'Glanza', 'Make Option D': '', 'Model Option D': '', 'Make Option E': '', 'Model Option E': '', 'Make': 'Tata', 'Model': 'Altroz'},
        'Toyota Glanza': {'Brand': 'Toyota', 'Segment': 'Premium Hatchback', 'Status': 'Current', 'Make Option A': 'Maruti', 'Model Option A': 'Baleno', 'Make Option B': 'Maruti', 'Model Option B': 'Swift', 'Make Option C': 'Tata', 'Model Option C': 'Altroz', 'Make Option D': '', 'Model Option D': '', 'Make Option E': '', 'Model Option E': '', 'Make': 'Toyota', 'Model': 'Glanza'},
        'VW Polo': {'Brand': 'Volkswagen', 'Segment': 'Premium Hatchback', 'Status': 'Discontinued', 'Make Option A': 'Toyota', 'Model Option A': 'Glanza', 'Make Option B': 'Honda', 'Model Option B': 'Jazz', 'Make Option C': 'Maruti', 'Model Option C': 'Swift', 'Make Option D': '', 'Model Option D': '', 'Make Option E': '', 'Model Option E': '', 'Make': 'volkswagen', 'Model': 'Polo'},
        'Ford Figo': {'Brand': 'Ford', 'Segment': 'Premium Hatchback', 'Status': 'Discontinued', 'Make Option A': 'Renault', 'Model Option A': 'Kwid', 'Make Option B': 'volkswagen', 'Model Option B': 'Polo', 'Make Option C': 'Maruti', 'Model Option C': 'Swift', 'Make Option D': '', 'Model Option D': '', 'Make Option E': '', 'Model Option E': '', 'Make': 'Ford', 'Model': 'Figo'},
        'Honda Jazz': {'Brand': 'Honda', 'Segment': 'Premium Hatchback', 'Status': 'Discontinued', 'Make Option A': 'Toyota', 'Model Option A': 'Glanza', 'Make Option B': 'volkswagen', 'Model Option B': 'Polo', 'Make Option C': 'Maruti', 'Model Option C': 'Swift', 'Make Option D': '', 'Model Option D': '', 'Make Option E': '', 'Model Option E': '', 'Make': 'Honda', 'Model': 'Jazz'},
        'Maruti Ignis': {'Brand': 'Maruti Suzuki', 'Segment': 'Micro SUV', 'Status': 'Discontinued', 'Make Option A': 'Maruti', 'Model Option A': 'Wagon R', 'Make Option B': 'Maruti', 'Model Option B': 'Celerio', 'Make Option C': 'Maruti', 'Model Option C': 'S-Presso', 'Make Option D': '', 'Model Option D': '', 'Make Option E': '', 'Model Option E': '', 'Make': 'Maruti', 'Model': 'Ignis'},
        'Maruti Dzire': {'Brand': 'Maruti Suzuki', 'Segment': 'Compact Sedan', 'Status': 'Current', 'Make Option A': 'Hyundai', 'Model Option A': 'Xcent', 'Make Option B': 'Honda', 'Model Option B': 'Amaze', 'Make Option C': 'Tata', 'Model Option C': 'Tigor', 'Make Option D': '', 'Model Option D': '', 'Make Option E': '', 'Model Option E': '', 'Make': 'Maruti', 'Model': 'Dzire'},
        'Honda Amaze': {'Brand': 'Honda', 'Segment': 'Compact Sedan', 'Status': 'Current', 'Make Option A': 'Maruti', 'Model Option A': 'Dzire', 'Make Option B': 'Hyundai', 'Model Option B': 'Xcent', 'Make Option C': 'Toyota', 'Model Option C': 'Etios', 'Make Option D': '', 'Model Option D': '', 'Make Option E': '', 'Model Option E': '', 'Make': 'Honda', 'Model': 'Amaze'},
        'Tata Tigor': {'Brand': 'Tata Motors', 'Segment': 'Compact Sedan', 'Status': 'Current', 'Make Option A': 'Maruti', 'Model Option A': 'Dzire', 'Make Option B': 'Hyundai', 'Model Option B': 'Xcent', 'Make Option C': 'Toyota', 'Model Option C': 'Etios', 'Make Option D': '', 'Model Option D': '', 'Make Option E': '', 'Model Option E': '', 'Make': 'Tata', 'Model': 'Tigor'},
        'Hyundai Aura': {'Brand': 'Hyundai', 'Segment': 'Compact Sedan', 'Status': 'Current', 'Make Option A': 'Hyundai', 'Model Option A': 'Xcent', 'Make Option B': 'Maruti', 'Model Option B': 'Dzire', 'Make Option C': 'Tata', 'Model Option C': 'Tigor', 'Make Option D': '', 'Model Option D': '', 'Make Option E': '', 'Model Option E': '', 'Make': 'Hyundai', 'Model': 'Aura'},
        'Hyundai Xcent': {'Brand': 'Hyundai', 'Segment': 'Compact Sedan', 'Status': 'Discontinued', 'Make Option A': 'Maruti', 'Model Option A': 'Dzire', 'Make Option B': 'Tata', 'Model Option B': 'Tigor', 'Make Option C': 'Toyota', 'Model Option C': 'Etios', 'Make Option D': '', 'Model Option D': '', 'Make Option E': '', 'Model Option E': '', 'Make': 'Hyundai', 'Model': 'Xcent'},
        'Ford Aspire': {'Brand': 'Ford', 'Segment': 'Compact Sedan', 'Status': 'Discontinued', 'Make Option A': 'Toyota', 'Model Option A': 'Etios', 'Make Option B': 'Maruti', 'Model Option B': 'Dzire', 'Make Option C': 'Hyundai', 'Model Option C': 'Xcent', 'Make Option D': '', 'Model Option D': '', 'Make Option E': '', 'Model Option E': '', 'Make': 'Ford', 'Model': 'Aspire'},
        'Tata Zest': {'Brand': 'Tata Motors', 'Segment': 'Compact Sedan', 'Status': 'Discontinued', 'Make Option A': 'Tata', 'Model Option A': 'Tigor', 'Make Option B': 'Maruti', 'Model Option B': 'Dzire', 'Make Option C': 'Toyota', 'Model Option C': 'Etios', 'Make Option D': '', 'Model Option D': '', 'Make Option E': '', 'Model Option E': '', 'Make': 'Tata', 'Model': 'Zest'},
        'VW Ameo': {'Brand': 'Volkswagen', 'Segment': 'Compact Sedan', 'Status': 'Discontinued', 'Make Option A': 'volkswagen', 'Model Option A': 'Vento', 'Make Option B': 'Toyota', 'Model Option B': 'Etios', 'Make Option C': 'Honda', 'Model Option C': 'Amaze', 'Make Option D': '', 'Model Option D': '', 'Make Option E': '', 'Model Option E': '', 'Make': 'volkswagen', 'Model': 'Ameo'},
        'Nissan Sunny': {'Brand': 'Nissan', 'Segment': 'Compact Sedan', 'Status': 'Discontinued', 'Make Option A': 'Maruti', 'Model Option A': 'Dzire', 'Make Option B': 'Hyundai', 'Model Option B': 'Xcent', 'Make Option C': 'Toyota', 'Model Option C': 'Etios', 'Make Option D': '', 'Model Option D': '', 'Make Option E': '', 'Model Option E': '', 'Make': 'Nissan', 'Model': 'Sunny'},
        'Toyota Etios': {'Brand': 'Toyota', 'Segment': 'Compact Sedan', 'Status': 'Discontinued', 'Make Option A': 'Maruti', 'Model Option A': 'Dzire', 'Make Option B': 'Hyundai', 'Model Option B': 'Xcent', 'Make Option C': 'Honda', 'Model Option C': 'Amaze', 'Make Option D': '', 'Model Option D': '', 'Make Option E': '', 'Model Option E': '', 'Make': 'Toyota', 'Model': 'Etios'},
        'Toyota Yaris': {'Brand': 'Toyota', 'Segment': 'Compact Sedan', 'Status': 'Discontinued', 'Make Option A': 'Maruti', 'Model Option A': 'Ciaz', 'Make Option B': 'Skoda', 'Model Option B': 'Rapid', 'Make Option C': 'volkswagen', 'Model Option C': 'Vento', 'Make Option D': '', 'Model Option D': '', 'Make Option E': '', 'Model Option E': '', 'Make': 'Toyota', 'Model': 'Yaris'},
        'Honda City': {'Brand': 'Honda', 'Segment': 'Mid Sedan', 'Status': 'Current', 'Make Option A': 'Hyundai', 'Model Option A': 'Verna', 'Make Option B': 'Skoda', 'Model Option B': 'Slavia', 'Make Option C': 'volkswagen', 'Model Option C': 'Virtus', 'Make Option D': '', 'Model Option D': '', 'Make Option E': '', 'Model Option E': '', 'Make': 'Honda', 'Model': 'City'},
        'Maruti Ciaz': {'Brand': 'Maruti Suzuki', 'Segment': 'Mid Sedan', 'Status': 'Current', 'Make Option A': 'Hyundai', 'Model Option A': 'Verna', 'Make Option B': 'Skoda', 'Model Option B': 'Rapid', 'Make Option C': 'Honda', 'Model Option C': 'City', 'Make Option D': '', 'Model Option D': '', 'Make Option E': '', 'Model Option E': '', 'Make': 'Maruti', 'Model': 'Ciaz'},
        'Hyundai Verna': {'Brand': 'Hyundai', 'Segment': 'Mid Sedan', 'Status': 'Current', 'Make Option A': 'Maruti', 'Model Option A': 'Ciaz', 'Make Option B': 'Honda', 'Model Option B': 'City', 'Make Option C': 'Skoda', 'Model Option C': 'Rapid', 'Make Option D': '', 'Model Option D': '', 'Make Option E': '', 'Model Option E': '', 'Make': 'Hyundai', 'Model': 'Verna'},
        'Skoda Rapid': {'Brand': 'Skoda', 'Segment': 'Mid Sedan', 'Status': 'Discontinued', 'Make Option A': 'volkswagen', 'Model Option A': 'Vento', 'Make Option B': 'Skoda', 'Model Option B': 'Slavia', 'Make Option C': 'Honda', 'Model Option C': 'City', 'Make Option D': '', 'Model Option D': '', 'Make Option E': '', 'Model Option E': '', 'Make': 'Skoda', 'Model': 'Rapid'},
        'Skoda Slavia': {'Brand': 'Skoda', 'Segment': 'Mid Sedan', 'Status': 'Current', 'Make Option A': 'volkswagen', 'Model Option A': 'Virtus', 'Make Option B': 'Skoda', 'Model Option B': 'Rapid', 'Make Option C': 'Honda', 'Model Option C': 'City', 'Make Option D': '', 'Model Option D': '', 'Make Option E': '', 'Model Option E': '', 'Make': 'Skoda', 'Model': 'Slavia'},
        'VW Vento': {'Brand': 'Volkswagen', 'Segment': 'Mid Sedan', 'Status': 'Discontinued', 'Make Option A': 'Skoda', 'Model Option A': 'Rapid', 'Make Option B': 'volkswagen', 'Model Option B': 'Virtus', 'Make Option C': 'Honda', 'Model Option C': 'City', 'Make Option D': '', 'Model Option D': '', 'Make Option E': '', 'Model Option E': '', 'Make': 'volkswagen', 'Model': 'Vento'},
        'VW Virtus': {'Brand': 'Volkswagen', 'Segment': 'Mid Sedan', 'Status': 'Current', 'Make Option A': 'Skoda', 'Model Option A': 'Slavia', 'Make Option B': 'volkswagen', 'Model Option B': 'Vento', 'Make Option C': 'Honda', 'Model Option C': 'City', 'Make Option D': '', 'Model Option D': '', 'Make Option E': '', 'Model Option E': '', 'Make': 'volkswagen', 'Model': 'Virtus'},
        'Toyota Corolla Altis': {'Brand': 'Toyota', 'Segment': 'Mid Sedan', 'Status': 'Discontinued', 'Make Option A': 'Hyundai', 'Model Option A': 'Verna', 'Make Option B': 'volkswagen', 'Model Option B': 'Vento', 'Make Option C': 'Skoda', 'Model Option C': 'Slavia', 'Make Option D': '', 'Model Option D': '', 'Make Option E': '', 'Model Option E': '', 'Make': 'Toyota', 'Model': 'Corolla Altis'},
        'Honda Civic': {'Brand': 'Honda', 'Segment': 'Premium Sedan', 'Status': 'Discontinued', 'Make Option A': 'Honda', 'Model Option A': 'City', 'Make Option B': 'Skoda', 'Model Option B': 'Octavia', 'Make Option C': 'Toyota', 'Model Option C': 'Camry', 'Make Option D': '', 'Model Option D': '', 'Make Option E': '', 'Model Option E': '', 'Make': 'Honda', 'Model': 'Civic'},
        'Hyundai Elantra': {'Brand': 'Hyundai', 'Segment': 'Premium Sedan', 'Status': 'Discontinued', 'Make Option A': 'Honda', 'Model Option A': 'Civic', 'Make Option B': 'Hyundai', 'Model Option B': 'Verna', 'Make Option C': 'Toyota', 'Model Option C': 'Corolla Altis', 'Make Option D': '', 'Model Option D': '', 'Make Option E': '', 'Model Option E': '', 'Make': 'Hyundai', 'Model': 'Elantra'},
        'Skoda Octavia': {'Brand': 'Skoda', 'Segment': 'Premium Sedan', 'Status': 'Current', 'Make Option A': 'Skoda', 'Model Option A': 'Superb', 'Make Option B': 'Toyota', 'Model Option B': 'Camry', 'Make Option C': 'Skoda', 'Model Option C': 'Slavia', 'Make Option D': '', 'Model Option D': '', 'Make Option E': '', 'Model Option E': '', 'Make': 'Skoda', 'Model': 'Octavia'},
        'Skoda Superb': {'Brand': 'Skoda', 'Segment': 'Premium Sedan', 'Status': 'Current', 'Make Option A': 'Skoda', 'Model Option A': 'Octavia', 'Make Option B': 'Toyota', 'Model Option B': 'Camry', 'Make Option C': 'Skoda', 'Model Option C': 'Slavia', 'Make Option D': '', 'Model Option D': '', 'Make Option E': '', 'Model Option E': '', 'Make': 'Skoda', 'Model': 'Superb'},
        'Toyota Camry': {'Brand': 'Toyota', 'Segment': 'Premium Sedan', 'Status': 'Current', 'Make Option A': 'Skoda', 'Model Option A': 'Superb', 'Make Option B': 'Toyota', 'Model Option B': 'Corolla Altis', 'Make Option C': 'Skoda', 'Model Option C': 'Octavia', 'Make Option D': '', 'Model Option D': '', 'Make Option E': '', 'Model Option E': '', 'Make': 'Toyota', 'Model': 'Camry'},
        'Tata Punch': {'Brand': 'Tata Motors', 'Segment': 'Micro SUV', 'Status': 'Current', 'Make Option A': 'Hyundai', 'Model Option A': 'Exter', 'Make Option B': 'Renault', 'Model Option B': 'Kiger', 'Make Option C': 'Nissan', 'Model Option C': 'Magnite', 'Make Option D': '', 'Model Option D': '', 'Make Option E': '', 'Model Option E': '', 'Make': 'Tata', 'Model': 'Punch'},
        'Hyundai Exter': {'Brand': 'Hyundai', 'Segment': 'Micro SUV', 'Status': 'Current', 'Make Option A': 'Tata', 'Model Option A': 'Punch', 'Make Option B': 'Renault', 'Model Option B': 'Kiger', 'Make Option C': 'Nissan', 'Model Option C': 'Magnite', 'Make Option D': '', 'Model Option D': '', 'Make Option E': '', 'Model Option E': '', 'Make': 'Hyundai', 'Model': 'Exter'},
        'Renault Kiger': {'Brand': 'Renault', 'Segment': 'Micro SUV', 'Status': 'Current', 'Make Option A': 'Tata', 'Model Option A': 'Punch', 'Make Option B': 'Hyundai', 'Model Option B': 'Exter', 'Make Option C': 'Nissan', 'Model Option C': 'Magnite', 'Make Option D': '', 'Model Option D': '', 'Make Option E': '', 'Model Option E': '', 'Make': 'Renault', 'Model': 'Kiger'},
        'Nissan Magnite': {'Brand': 'Nissan', 'Segment': 'Micro SUV', 'Status': 'Current', 'Make Option A': 'Renault', 'Model Option A': 'Kiger', 'Make Option B': 'Tata', 'Model Option B': 'Punch', 'Make Option C': 'Hyundai', 'Model Option C': 'Exter', 'Make Option D': '', 'Model Option D': '', 'Make Option E': '', 'Model Option E': '', 'Make': 'Nissan', 'Model': 'Magnite'},
        'Ford Freestyle': {'Brand': 'Ford', 'Segment': 'Micro SUV', 'Status': 'Discontinued', 'Make Option A': 'Tata', 'Model Option A': 'Punch', 'Make Option B': 'Hyundai', 'Model Option B': 'Exter', 'Make Option C': 'Mahindra', 'Model Option C': 'KUV100', 'Make Option D': '', 'Model Option D': '', 'Make Option E': '', 'Model Option E': '', 'Make': 'Ford', 'Model': 'Freestyle'},
        'Mahindra KUV100': {'Brand': 'Mahindra', 'Segment': 'Micro SUV', 'Status': 'Discontinued', 'Make Option A': 'Tata', 'Model Option A': 'Punch', 'Make Option B': 'Hyundai', 'Model Option B': 'Exter', 'Make Option C': 'Renault', 'Model Option C': 'Kiger', 'Make Option D': '', 'Model Option D': '', 'Make Option E': '', 'Model Option E': '', 'Make': 'Mahindra', 'Model': 'KUV100'},
        'Skoda Kylaq': {'Brand': 'Skoda', 'Segment': 'Micro SUV', 'Status': 'Current', 'Make Option A': 'Kia', 'Model Option A': 'Sonet', 'Make Option B': 'Hyundai', 'Model Option B': 'Venue', 'Make Option C': 'Tata', 'Model Option C': 'Nexon', 'Make Option D': '', 'Model Option D': '', 'Make Option E': '', 'Model Option E': '', 'Make': 'Skoda', 'Model': 'Kylaq'},
        'Tata Nexon': {'Brand': 'Tata Motors', 'Segment': 'Compact SUV', 'Status': 'Current', 'Make Option A': 'Maruti', 'Model Option A': 'Brezza', 'Make Option B': 'Hyundai', 'Model Option B': 'Venue', 'Make Option C': 'Kia', 'Model Option C': 'Sonet', 'Make Option D': '', 'Model Option D': '', 'Make Option E': '', 'Model Option E': '', 'Make': 'Tata', 'Model': 'Nexon'},
        'Maruti Brezza': {'Brand': 'Maruti Suzuki', 'Segment': 'Compact SUV', 'Status': 'Current', 'Make Option A': 'Hyundai', 'Model Option A': 'Venue', 'Make Option B': 'Tata', 'Model Option B': 'Nexon', 'Make Option C': 'Kia', 'Model Option C': 'Sonet', 'Make Option D': '', 'Model Option D': '', 'Make Option E': '', 'Model Option E': '', 'Make': 'Maruti', 'Model': 'Brezza'},
        'Maruti Fronx': {'Brand': 'Maruti Suzuki', 'Segment': 'Compact SUV', 'Status': 'Current', 'Make Option A': 'Maruti', 'Model Option A': 'Brezza', 'Make Option B': 'Toyota', 'Model Option B': 'Urban Cruiser Taisor', 'Make Option C': 'Tata', 'Model Option C': 'Nexon', 'Make Option D': '', 'Model Option D': '', 'Make Option E': '', 'Model Option E': '', 'Make': 'Maruti', 'Model': 'Fronx'},
        'Kia Sonet': {'Brand': 'Kia', 'Segment': 'Compact SUV', 'Status': 'Current', 'Make Option A': 'Hyundai', 'Model Option A': 'Venue', 'Make Option B': 'Tata', 'Model Option B': 'Nexon', 'Make Option C': 'Maruti', 'Model Option C': 'Brezza', 'Make Option D': '', 'Model Option D': '', 'Make Option E': '', 'Model Option E': '', 'Make': 'Kia', 'Model': 'Sonet'},
        'Hyundai Venue': {'Brand': 'Hyundai', 'Segment': 'Compact SUV', 'Status': 'Current', 'Make Option A': 'Kia', 'Model Option A': 'Sonet', 'Make Option B': 'Tata', 'Model Option B': 'Nexon', 'Make Option C': 'Maruti', 'Model Option C': 'Brezza', 'Make Option D': '', 'Model Option D': '', 'Make Option E': '', 'Model Option E': '', 'Make': 'Hyundai', 'Model': 'Venue'},
        'Mahindra XUV3XO': {'Brand': 'Mahindra', 'Segment': 'Compact SUV', 'Status': 'Current', 'Make Option A': 'Tata', 'Model Option A': 'Nexon', 'Make Option B': 'Maruti', 'Model Option B': 'Brezza', 'Make Option C': 'Hyundai', 'Model Option C': 'Venue', 'Make Option D': '', 'Model Option D': '', 'Make Option E': '', 'Model Option E': '', 'Make': 'Mahindra', 'Model': 'XUV3XO'},
        'Ford EcoSport': {'Brand': 'Ford', 'Segment': 'Compact SUV', 'Status': 'Discontinued', 'Make Option A': 'Maruti', 'Model Option A': 'Brezza', 'Make Option B': 'Hyundai', 'Model Option B': 'Venue', 'Make Option C': 'Tata', 'Model Option C': 'Nexon', 'Make Option D': '', 'Model Option D': '', 'Make Option E': '', 'Model Option E': '', 'Make': 'Ford', 'Model': 'EcoSport'},
        'Honda WR-V': {'Brand': 'Honda', 'Segment': 'Compact SUV', 'Status': 'Discontinued', 'Make Option A': 'Ford', 'Model Option A': 'EcoSport', 'Make Option B': 'Toyota', 'Model Option B': 'Urban Cruiser', 'Make Option C': 'Tata', 'Model Option C': 'Nexon', 'Make Option D': '', 'Model Option D': '', 'Make Option E': '', 'Model Option E': '', 'Make': 'Honda', 'Model': 'WR-V'},
        'Honda Elevate': {'Brand': 'Honda', 'Segment': 'Compact SUV', 'Status': 'Current', 'Make Option A': 'Hyundai', 'Model Option A': 'Venue', 'Make Option B': 'Kia', 'Model Option B': 'Sonet', 'Make Option C': 'MG', 'Model Option C': 'Astor', 'Make Option D': '', 'Model Option D': '', 'Make Option E': '', 'Model Option E': '', 'Make': 'Honda', 'Model': 'Elevate'},
        'Renault Duster': {'Brand': 'Renault', 'Segment': 'Compact SUV', 'Status': 'Discontinued', 'Make Option A': 'Ford', 'Model Option A': 'EcoSport', 'Make Option B': 'Tata', 'Model Option B': 'Nexon', 'Make Option C': 'Maruti', 'Model Option C': 'Brezza', 'Make Option D': '', 'Model Option D': '', 'Make Option E': '', 'Model Option E': '', 'Make': 'Renault', 'Model': 'Duster'},
        'Renault Captur': {'Brand': 'Renault', 'Segment': 'Compact SUV', 'Status': 'Discontinued', 'Make Option A': 'Renault', 'Model Option A': 'Duster', 'Make Option B': 'Maruti', 'Model Option B': 'Brezza', 'Make Option C': 'Ford', 'Model Option C': 'EcoSport', 'Make Option D': '', 'Model Option D': '', 'Make Option E': '', 'Model Option E': '', 'Make': 'Renault', 'Model': 'Captur'},
        'Toyota Urban Cruiser': {'Brand': 'Toyota', 'Segment': 'Compact SUV', 'Status': 'Discontinued', 'Make Option A': 'Maruti', 'Model Option A': 'Brezza', 'Make Option B': 'Ford', 'Model Option B': 'EcoSport', 'Make Option C': 'Maruti', 'Model Option C': 'Brezza', 'Make Option D': '', 'Model Option D': '', 'Make Option E': '', 'Model Option E': '', 'Make': 'Toyota', 'Model': 'Urban Cruiser'},
        'Toyota Urban Cruiser Taisor': {'Brand': 'Toyota', 'Segment': 'Compact SUV', 'Status': 'Current', 'Make Option A': 'Ford', 'Model Option A': 'EcoSport', 'Make Option B': 'Maruti', 'Model Option B': 'Fronx', 'Make Option C': 'Tata', 'Model Option C': 'Nexon', 'Make Option D': '', 'Model Option D': '', 'Make Option E': '', 'Model Option E': '', 'Make': 'Toyota', 'Model': 'Urban Cruiser Taisor'},
        'Tata Curvv': {'Brand': 'Tata Motors', 'Segment': 'Compact SUV', 'Status': 'Current', 'Make Option A': 'Tata', 'Model Option A': 'Nexon', 'Make Option B': 'Kia', 'Model Option B': 'Sonet', 'Make Option C': 'Mahindra', 'Model Option C': 'XUV3XO', 'Make Option D': '', 'Model Option D': '', 'Make Option E': '', 'Model Option E': '', 'Make': 'Tata', 'Model': 'Curvv'},
        'MG Astor': {'Brand': 'MG Motor', 'Segment': 'Compact SUV', 'Status': 'Current', 'Make Option A': 'Honda', 'Model Option A': 'Elevate', 'Make Option B': 'Tata', 'Model Option B': 'Nexon', 'Make Option C': 'Kia', 'Model Option C': 'Sonet', 'Make Option D': '', 'Model Option D': '', 'Make Option E': '', 'Model Option E': '', 'Make': 'MG', 'Model': 'Astor'},
        'Hyundai Creta': {'Brand': 'Hyundai', 'Segment': 'Mid SUV', 'Status': 'Current', 'Make Option A': 'Kia', 'Model Option A': 'Seltos', 'Make Option B': 'Maruti', 'Model Option B': 'Grand Vitara', 'Make Option C': 'Skoda', 'Model Option C': 'Kushaq', 'Make Option D': '', 'Model Option D': '', 'Make Option E': '', 'Model Option E': '', 'Make': 'Hyundai', 'Model': 'Creta'},
        'Kia Seltos': {'Brand': 'Kia', 'Segment': 'Mid SUV', 'Status': 'Current', 'Make Option A': 'Hyundai', 'Model Option A': 'Creta', 'Make Option B': 'Maruti', 'Model Option B': 'Grand Vitara', 'Make Option C': 'Skoda', 'Model Option C': 'Kushaq', 'Make Option D': '', 'Model Option D': '', 'Make Option E': '', 'Model Option E': '', 'Make': 'Kia', 'Model': 'Seltos'},
        'Maruti Grand Vitara': {'Brand': 'Maruti Suzuki', 'Segment': 'Mid SUV', 'Status': 'Current', 'Make Option A': 'Hyundai', 'Model Option A': 'Creta', 'Make Option B': 'Kia', 'Model Option B': 'Seltos', 'Make Option C': 'Skoda', 'Model Option C': 'Kushaq', 'Make Option D': '', 'Model Option D': '', 'Make Option E': '', 'Model Option E': '', 'Make': 'Maruti', 'Model': 'Grand Vitara'},
        'Toyota Urban Cruiser Hyryder': {'Brand': 'Toyota', 'Segment': 'Mid SUV', 'Status': 'Current', 'Make Option A': 'Maruti', 'Model Option A': 'Grand Vitara', 'Make Option B': 'Hyundai', 'Model Option B': 'Creta', 'Make Option C': 'Kia', 'Model Option C': 'Seltos', 'Make Option D': '', 'Model Option D': '', 'Make Option E': '', 'Model Option E': '', 'Make': 'Toyota', 'Model': 'Urban Cruiser Hyryder'},
        'Skoda Kushaq': {'Brand': 'Skoda', 'Segment': 'Mid SUV', 'Status': 'Current', 'Make Option A': 'volkswagen', 'Model Option A': 'Taigun', 'Make Option B': 'Kia', 'Model Option B': 'Seltos', 'Make Option C': 'Hyundai', 'Model Option C': 'Creta', 'Make Option D': '', 'Model Option D': '', 'Make Option E': '', 'Model Option E': '', 'Make': 'Skoda', 'Model': 'Kushaq'},
        'VW Taigun': {'Brand': 'Volkswagen', 'Segment': 'Mid SUV', 'Status': 'Current', 'Make Option A': 'Skoda', 'Model Option A': 'Kushaq', 'Make Option B': 'Kia', 'Model Option B': 'Seltos', 'Make Option C': 'Hyundai', 'Model Option C': 'Creta', 'Make Option D': '', 'Model Option D': '', 'Make Option E': '', 'Model Option E': '', 'Make': 'volkswagen', 'Model': 'Taigun'},
        'Maruti S-Cross': {'Brand': 'Maruti Suzuki', 'Segment': 'Mid SUV', 'Status': 'Discontinued', 'Make Option A': 'Maruti', 'Model Option A': 'Brezza', 'Make Option B': 'Hyundai', 'Model Option B': 'Creta', 'Make Option C': 'Maruti', 'Model Option C': 'Grand Vitara', 'Make Option D': '', 'Model Option D': '', 'Make Option E': '', 'Model Option E': '', 'Make': 'Maruti', 'Model': 'S-Cross'},
        'Nissan Kicks': {'Brand': 'Nissan', 'Segment': 'Mid SUV', 'Status': 'Discontinued', 'Make Option A': 'Renault', 'Model Option A': 'Duster', 'Make Option B': 'Hyundai', 'Model Option B': 'Creta', 'Make Option C': 'Ford', 'Model Option C': 'EcoSport', 'Make Option D': '', 'Model Option D': '', 'Make Option E': '', 'Model Option E': '', 'Make': 'Nissan', 'Model': 'Kicks'},
        'VW T-Roc': {'Brand': 'Volkswagen', 'Segment': 'Mid SUV', 'Status': 'Discontinued', 'Make Option A': 'volkswagen', 'Model Option A': 'Taigun', 'Make Option B': 'Skoda', 'Model Option B': 'Kushaq', 'Make Option C': 'MG', 'Model Option C': 'Hector', 'Make Option D': '', 'Model Option D': '', 'Make Option E': '', 'Model Option E': '', 'Make': 'volkswagen', 'Model': 'T-Roc'},
        'Jeep Compass': {'Brand': 'Jeep', 'Segment': 'Mid SUV', 'Status': 'Current', 'Make Option A': 'MG', 'Model Option A': 'Hector', 'Make Option B': 'Mahindra', 'Model Option B': 'XUV700', 'Make Option C': 'volkswagen', 'Model Option C': 'Taigun', 'Make Option D': '', 'Model Option D': '', 'Make Option E': '', 'Model Option E': '', 'Make': 'Jeep', 'Model': 'Compass'},
        'Mahindra Scorpio': {'Brand': 'Mahindra', 'Segment': 'Full/Lifestyle SUV', 'Status': 'Current', 'Make Option A': 'Mahindra', 'Model Option A': 'Thar', 'Make Option B': 'Mahindra', 'Model Option B': 'XUV500', 'Make Option C': 'Tata', 'Model Option C': 'Harrier', 'Make Option D': '', 'Model Option D': '', 'Make Option E': '', 'Model Option E': '', 'Make': 'Mahindra', 'Model': 'Scorpio'},
        'Mahindra Thar': {'Brand': 'Mahindra', 'Segment': 'Full/Lifestyle SUV', 'Status': 'Current', 'Make Option A': 'Mahindra', 'Model Option A': 'Scorpio', 'Make Option B': 'Mahindra', 'Model Option B': 'XUV500', 'Make Option C': 'Tata', 'Model Option C': 'Harrier', 'Make Option D': '', 'Model Option D': '', 'Make Option E': '', 'Model Option E': '', 'Make': 'Mahindra', 'Model': 'Thar'},
        'Mahindra XUV700': {'Brand': 'Mahindra', 'Segment': 'Full/Lifestyle SUV', 'Status': 'Current', 'Make Option A': 'Tata', 'Model Option A': 'Harrier', 'Make Option B': 'MG', 'Model Option B': 'Hector', 'Make Option C': 'Hyundai', 'Model Option C': 'Tucson', 'Make Option D': '', 'Model Option D': '', 'Make Option E': '', 'Model Option E': '', 'Make': 'Mahindra', 'Model': 'XUV700'},
        'Mahindra XUV500': {'Brand': 'Mahindra', 'Segment': 'Full/Lifestyle SUV', 'Status': 'Discontinued', 'Make Option A': 'Tata', 'Model Option A': 'Harrier', 'Make Option B': 'MG', 'Model Option B': 'Hector', 'Make Option C': 'Hyundai', 'Model Option C': 'Tucson', 'Make Option D': '', 'Model Option D': '', 'Make Option E': '', 'Model Option E': '', 'Make': 'Mahindra', 'Model': 'XUV500'},
        'Tata Harrier': {'Brand': 'Tata Motors', 'Segment': 'Full/Lifestyle SUV', 'Status': 'Current', 'Make Option A': 'Tata', 'Model Option A': 'Safari', 'Make Option B': 'Mahindra', 'Model Option B': 'XUV700', 'Make Option C': 'MG', 'Model Option C': 'Hector', 'Make Option D': '', 'Model Option D': '', 'Make Option E': '', 'Model Option E': '', 'Make': 'Tata', 'Model': 'Harrier'},
        'Tata Safari': {'Brand': 'Tata Motors', 'Segment': 'Full/Lifestyle SUV', 'Status': 'Current', 'Make Option A': 'Tata', 'Model Option A': 'Harrier', 'Make Option B': 'Mahindra', 'Model Option B': 'XUV700', 'Make Option C': 'Mahindra', 'Model Option C': 'Thar', 'Make Option D': '', 'Model Option D': '', 'Make Option E': '', 'Model Option E': '', 'Make': 'Tata', 'Model': 'Safari'},
        'MG Hector': {'Brand': 'MG Motor', 'Segment': 'Full/Lifestyle SUV', 'Status': 'Current', 'Make Option A': 'Tata', 'Model Option A': 'Harrier', 'Make Option B': 'Mahindra', 'Model Option B': 'XUV700', 'Make Option C': 'Hyundai', 'Model Option C': 'Tucson', 'Make Option D': '', 'Model Option D': '', 'Make Option E': '', 'Model Option E': '', 'Make': 'MG', 'Model': 'Hector'},
        'Tata Hexa': {'Brand': 'Tata Motors', 'Segment': 'Full/Lifestyle SUV', 'Status': 'Discontinued', 'Make Option A': 'Tata', 'Model Option A': 'Harrier', 'Make Option B': 'Mahindra', 'Model Option B': 'XUV500', 'Make Option C': 'MG', 'Model Option C': 'Hector', 'Make Option D': '', 'Model Option D': '', 'Make Option E': '', 'Model Option E': '', 'Make': 'Tata', 'Model': 'Hexa'},
        'Hyundai Tucson': {'Brand': 'Hyundai', 'Segment': 'Full/Lifestyle SUV', 'Status': 'Current', 'Make Option A': 'Mahindra', 'Model Option A': 'XUV700', 'Make Option B': 'Tata', 'Model Option B': 'Harrier', 'Make Option C': 'MG', 'Model Option C': 'Hector', 'Make Option D': '', 'Model Option D': '', 'Make Option E': '', 'Model Option E': '', 'Make': 'Hyundai', 'Model': 'Tucson'},
        'Honda CR-V': {'Brand': 'Honda', 'Segment': 'Premium SUV', 'Status': 'Discontinued', 'Make Option A': 'Hyundai', 'Model Option A': 'Tucson', 'Make Option B': 'Mahindra', 'Model Option B': 'XUV500', 'Make Option C': 'Mahindra', 'Model Option C': 'XUV700', 'Make Option D': '', 'Model Option D': '', 'Make Option E': '', 'Model Option E': '', 'Make': 'Honda', 'Model': 'CR-V'},
        'Hyundai Santa Fe': {'Brand': 'Hyundai', 'Segment': 'Premium SUV', 'Status': 'Current', 'Make Option A': 'Honda', 'Model Option A': 'CR-V', 'Make Option B': 'Hyundai', 'Model Option B': 'Tucson', 'Make Option C': 'Mahindra', 'Model Option C': 'XUV500', 'Make Option D': '', 'Model Option D': '', 'Make Option E': '', 'Model Option E': '', 'Make': 'Hyundai', 'Model': 'Santa Fe'},
        'Mahindra Bolero': {'Brand': 'Mahindra', 'Segment': 'Utility SUV', 'Status': 'Current', 'Make Option A': 'Mahindra', 'Model Option A': 'TUV300', 'Make Option B': 'Mahindra', 'Model Option B': 'XUV500', 'Make Option C': 'Mahindra', 'Model Option C': 'Scorpio', 'Make Option D': '', 'Model Option D': '', 'Make Option E': '', 'Model Option E': '', 'Make': 'Mahindra', 'Model': 'Bolero'},
        'Mahindra TUV300': {'Brand': 'Mahindra', 'Segment': 'Utility SUV', 'Status': 'Discontinued', 'Make Option A': 'Mahindra', 'Model Option A': 'Bolero', 'Make Option B': 'Mahindra', 'Model Option B': 'Thar', 'Make Option C': 'Mahindra', 'Model Option C': 'XUV500', 'Make Option D': '', 'Model Option D': '', 'Make Option E': '', 'Model Option E': '', 'Make': 'Mahindra', 'Model': 'TUV300'},
        'Maruti Ertiga': {'Brand': 'Maruti Suzuki', 'Segment': 'Compact MUV', 'Status': 'Current', 'Make Option A': 'Maruti', 'Model Option A': 'XL6', 'Make Option B': 'Renault', 'Model Option B': 'Triber', 'Make Option C': 'Honda', 'Model Option C': 'Mobilio', 'Make Option D': '', 'Model Option D': '', 'Make Option E': '', 'Model Option E': '', 'Make': 'Maruti', 'Model': 'Ertiga'},
        'Maruti XL6': {'Brand': 'Maruti Suzuki', 'Segment': 'Compact MUV', 'Status': 'Current', 'Make Option A': 'Maruti', 'Model Option A': 'Ertiga', 'Make Option B': 'Honda', 'Model Option B': 'BR-V', 'Make Option C': 'Renault', 'Model Option C': 'Triber', 'Make Option D': '', 'Model Option D': '', 'Make Option E': '', 'Model Option E': '', 'Make': 'Maruti', 'Model': 'XL6'},
        'Renault Triber': {'Brand': 'Renault', 'Segment': 'Compact MUV', 'Status': 'Current', 'Make Option A': 'Datsun', 'Model Option A': 'GO+', 'Make Option B': 'Maruti', 'Model Option B': 'Ertiga', 'Make Option C': 'Maruti', 'Model Option C': 'XL6', 'Make Option D': '', 'Model Option D': '', 'Make Option E': '', 'Model Option E': '', 'Make': 'Renault', 'Model': 'Triber'},
        'Datsun GO+': {'Brand': 'Datsun', 'Segment': 'Compact MUV', 'Status': 'Discontinued', 'Make Option A': 'Renault', 'Model Option A': 'Triber', 'Make Option B': 'Maruti', 'Model Option B': 'Ertiga', 'Make Option C': 'Maruti', 'Model Option C': 'XL6', 'Make Option D': '', 'Model Option D': '', 'Make Option E': '', 'Model Option E': '', 'Make': 'Datsun', 'Model': 'GO+'},
        'Honda BR-V': {'Brand': 'Honda', 'Segment': 'Compact MUV', 'Status': 'Discontinued', 'Make Option A': 'Maruti', 'Model Option A': 'Ertiga', 'Make Option B': 'Honda', 'Model Option B': 'Mobilio', 'Make Option C': 'Maruti', 'Model Option C': 'XL6', 'Make Option D': '', 'Model Option D': '', 'Make Option E': '', 'Model Option E': '', 'Make': 'Honda', 'Model': 'BR-V'},
        'Honda Mobilio': {'Brand': 'Honda', 'Segment': 'Compact MUV', 'Status': 'Discontinued', 'Make Option A': 'Maruti', 'Model Option A': 'Ertiga', 'Make Option B': 'Honda', 'Model Option B': 'BR-V', 'Make Option C': 'Maruti', 'Model Option C': 'XL6', 'Make Option D': '', 'Model Option D': '', 'Make Option E': '', 'Model Option E': '', 'Make': 'Honda', 'Model': 'Mobilio'},
        'Toyota Innova': {'Brand': 'Toyota', 'Segment': 'Mid/Premium MUV', 'Status': 'Current', 'Make Option A': 'Hyundai', 'Model Option A': 'Alcazar', 'Make Option B': 'Maruti', 'Model Option B': 'XL6', 'Make Option C': 'Kia', 'Model Option C': 'Carens', 'Make Option D': '', 'Model Option D': '', 'Make Option E': '', 'Model Option E': '', 'Make': 'Toyota', 'Model': 'Innova'},
        'Kia Carens': {'Brand': 'Kia', 'Segment': 'Mid/Premium MUV', 'Status': 'Current', 'Make Option A': 'Maruti', 'Model Option A': 'XL6', 'Make Option B': 'Maruti', 'Model Option B': 'Ertiga', 'Make Option C': 'Toyota', 'Model Option C': 'Innova', 'Make Option D': '', 'Model Option D': '', 'Make Option E': '', 'Model Option E': '', 'Make': 'Kia', 'Model': 'Carens'},
        'Hyundai Alcazar': {'Brand': 'Hyundai', 'Segment': 'Mid/Premium MUV', 'Status': 'Current', 'Make Option A': 'MG', 'Model Option A': 'Hector', 'Make Option B': 'Mahindra', 'Model Option B': 'XUV700', 'Make Option C': 'Tata', 'Model Option C': 'Harrier', 'Make Option D': '', 'Model Option D': '', 'Make Option E': '', 'Model Option E': '', 'Make': 'Hyundai', 'Model': 'Alcazar'},
        'Maruti Eeco': {'Brand': 'Maruti Suzuki', 'Segment': 'Van', 'Status': 'Current', 'Make Option A': 'Datsun', 'Model Option A': 'GO+', 'Make Option B': 'Renault', 'Model Option B': 'Triber', 'Make Option C': 'Maruti', 'Model Option C': 'Ertiga', 'Make Option D': '', 'Model Option D': '', 'Make Option E': '', 'Model Option E': '', 'Make': 'Maruti', 'Model': 'Eeco'},
        'Toyota Fortuner': {'Brand': 'Toyota', 'Segment': 'Full-Size SUV', 'Status': 'Current', 'Make Option A': 'MG', 'Model Option A': 'Gloster', 'Make Option B': 'Hyundai', 'Model Option B': 'Tucson', 'Make Option C': 'Ford', 'Model Option C': 'Endeavour', 'Make Option D': '', 'Model Option D': '', 'Make Option E': '', 'Model Option E': '', 'Make': 'Toyota', 'Model': 'Fortuner'},
    }

	def get_similar_cars_row(make_model: str, score_cutoff: int = 60):
		if not make_model:
			return None
		needle = make_model.strip().casefold()
		for key, row in SIMILAR_CARS.items():
			if key.casefold() == needle:
				return {"Model Make": key, **row}
		match = process.extractOne(
			make_model,
			SIMILAR_CARS.keys(),
			scorer=fuzz.WRatio,
			score_cutoff=score_cutoff,
		)
		if match is None:
			return None
		best_key, _score, _ = match
		return {"Model Make": best_key, **SIMILAR_CARS[best_key]}

	# ──────────────────────────────────────────────────────────────────────────
	# return_cars — performs one API call, ranks/filters results.
	# ──────────────────────────────────────────────────────────────────────────
	async def return_cars(
		ctx,
		payload: dict,
		function_name: str,
		diversify: bool = False,
		prefer_model: str = "",
		prefer_make: str = "",
	):
		if payload.get("city", "") == "vizag":
			payload.update({"city": "visakhapatnam"})
		if payload.get("make", "") == "maruti":
			payload.update({"make": "maruti-suzuki"})
		if payload.get("model", "") == "maruti":
			payload.update({"model": "maruti-suzuki"})
		if payload.get("make", "") == "alto":
			payload.update({"make": "alto,alto-800,alto-k10"})
		if payload.get("model", "") == "alto":
			payload.update({"model": "alto,alto-800,alto-k10"})

		agent = ctx.session.current_agent
		dial_info = getattr(agent, "dial_info", {}) or {}
		job_ctx = get_job_context()
		curr_prompt = dial_info.get("system_prompt", False)
		if curr_prompt:
			key_map = {"max_mileage": "max_km_driven"}
			updated_prompt = curr_prompt
			for key, value in payload.items():
				placeholder = key_map.get(key, key)
				updated_prompt = updated_prompt.replace(f"{{{placeholder}}}", str(value).strip())
			if payload.get("city", False):
				updated_prompt = updated_prompt.replace("{{city}}", payload.get("city", "").strip())
				updated_prompt = updated_prompt.replace("{city}", payload.get("city", "").strip())
				updated_prompt = updated_prompt.replace(
					"{available_hubs}",
					get_hubs_as_string(payload.get("city", "").strip()).get("hubs", ""),
				)
			await agent.update_instructions(updated_prompt)

		fixed_params = {
			'product_type': 'cars',
			'category': 'used',
			'page': '1',
			'show_max_on_assured': 'true',
			'custom_budget_sort': 'true',
			'prioritize_filter_listing': 'true',
			'high_intent_required': 'false',
			'active_banner': 'true',
			'availability': 'available',
		}

		if payload.get("min_price") == 0:
			payload.update({"min_price": ""})
		elif isinstance(payload.get("min_price"), float):
			min_p = payload.get("min_price") * 100000 if payload.get("min_price") < 10000 else payload.get("min_price")
			payload.update({"min_price": str(int(min_p))})

		if payload.get("max_price") == 0:
			payload.update({"max_price": ""})
		elif isinstance(payload.get("max_price"), float):
			max_p = payload.get("max_price") * 100000 if payload.get("max_price") < 10000 else payload.get("max_price")
			if function_name == "get_cars_according_to_user_choice_with_extra_budget":
				fixed_params.update({"o": "price"})
			else:
				fixed_params.update({"o": "-price"})
			payload.update({"max_price": str(int(max_p))})
		if function_name == "get_cars_according_to_user_choice_with_extra_budget":
			fixed_params.update({"o": "price"})

		replacements = {
			"डिज़ायर": "dzire", "डिजायर": "dzire",
			"desire": "dzire", "dezire": "dzire",
		}
		for key in ("model", "make"):
			if payload.get(key):
				val = payload[key]
				for old, new in replacements.items():
					val = val.replace(old, new)
				if " " in val:
					with_dash = val.replace(" ", "-")
					val = f"{val},{with_dash}"
				payload[key] = val

		ist = pytz.timezone("Asia/Kolkata")
		now_ist = datetime.now(ist)

		def record(succ: bool, resp_data=None):
			new_f = {
				"name": function_name,
				"parameters": payload,
				"success": succ,
				"timestamp": now_ist.isoformat(),
				"response": resp_data,
			}
			add_functions_called(get_job_context(), new_f)

		url = "https://api.spinny.com/v3/api/listing/v3/"
		make_local = payload.get("make", "")
		model_local = payload.get("model", "")
		copied_payload = payload.copy()
		if model_local and make_local:
			copied_payload.pop("make", None)

		async with httpx.AsyncClient() as client:
			for _ in range(2):
				resp = await client.get(url, params=get_params(fixed_params, copied_payload))
				if resp.status_code == 200:
					break
				await asyncio.sleep(1)

		if resp.status_code == 200:
			rj = resp.json()
			filtered_count = rj.get("count", 0)
			filtered = rj.get("results", []) or []

			# Swap-make-and-model retry (unchanged from original)
			if function_name != "check_model_availability" and filtered_count == 0 and (make_local or model_local):
				for _swap_attempt in range(3):
					payload.update({"make": model_local.lower(), "model": make_local.lower()})
					make_local = payload.get("make", "")
					model_local = payload.get("model", "")
					copied_payload = payload.copy()
					if model_local and make_local:
						copied_payload.pop("make", None)
					async with httpx.AsyncClient() as client:
						for _ in range(2):
							resp = await client.get(url, params=get_params(fixed_params, copied_payload))
							if resp.status_code == 200:
								break
							await asyncio.sleep(1)
					if resp.status_code != 200:
						break
					rj = resp.json()
					filtered_count = rj.get("count", 0)
					filtered = rj.get("results", []) or []
					if filtered_count > 0 or not (make_local and model_local):
						break

			additional_message = ''
			existing_pitched = job_ctx.proc.userdata.setdefault("pitched_cars_lead_ids", [])
			logger.info(f"Existing pitched cars lead_ids: {existing_pitched}")
			if filtered_count and existing_pitched:
				existing_pitched_str = {str(lead_id) for lead_id in existing_pitched}
				new_filtered = [
					item for item in filtered
					if str(item.get("id")) not in existing_pitched_str
				]
				filtered = new_filtered
				filtered_count = len(filtered)

			city_payload = payload.get("city", "").strip().lower()
			if filtered_count and city_payload in ["delhi", "gurgaon", "noida", "faridabad", "ghaziabad"]:
				new_filtered = [
					item for item in filtered
					if item.get("city", "").strip().lower() == city_payload
				]
				if new_filtered:
					filtered = new_filtered
					filtered_count = len(filtered)
					logger.info(f"After city-level filtering, found ({filtered_count}) cars from {function_name}")
				else:
					additional_message = f"The system could not find cars in {city_payload} with given choices, then system searched for nearby locations of delhi-ncr, and then "

			count = num2words(filtered_count, lang='en_IN')
			if filtered_count == 0:
				record(True, { "msg": "no cars found" })
				return {
					"success": True,
					"message": f"sorry, no cars found for the given preferences.",
					"data": [],
					"count": filtered_count,
					"count_in_words": count
				}

			def rank_filtered(filtered, target_model, target_make, top_n=None):
				ranked = []
				for item in filtered:
					model_score = fuzz.token_set_ratio(str(item.get("model", "")), target_model)
					make_score = fuzz.token_set_ratio(str(item.get("make", "")), target_make)
					final_score = (model_score + make_score) / 2
					ranked.append({**item, "score": final_score})
				ranked.sort(key=lambda x: x["score"], reverse=True)
				return ranked if top_n is None else ranked[:top_n]

			def diversify_by_model(cars, max_total=15):
				from collections import OrderedDict
				model_buckets = OrderedDict()
				for car in cars:
					model_name = car.get("model", "unknown").lower()
					if model_name not in model_buckets:
						model_buckets[model_name] = []
					model_buckets[model_name].append(car)
				for model_name in model_buckets:
					model_buckets[model_name].sort(key=lambda x: x.get("price", 0), reverse=True)
				result = []
				while len(result) < max_total:
					added_any = False
					for model_name in list(model_buckets.keys()):
						bucket = model_buckets[model_name]
						taken = 0
						while taken < 1 and bucket and len(result) < max_total:
							result.append(bucket.pop(0))
							taken += 1
							added_any = True
						if not bucket:
							del model_buckets[model_name]
					if not added_any:
						break
				return result

			model_local = payload.get("model", "")
			make_local = payload.get("make", "")

			# ─── Ranking decision ──────────────────────────────────────
			HARSH_FUZZY_THRESHOLD = 70
			if function_name == "check_model_availability":
				ranked_filtered = filtered

			elif prefer_model or prefer_make:
				target_norm = prefer_model or prefer_make
				scored = []
				for item in filtered:
					car_model_norm = _norm(item.get("model", ""))
					car_make_norm = _norm(item.get("make", ""))

					if prefer_model and (
						car_model_norm == prefer_model
						or prefer_model in car_model_norm
						or car_model_norm in prefer_model
					):
						tier = 0
					elif prefer_make and car_make_norm == prefer_make:
						tier = 1
					else:
						tier = 2

					family_score = max(
						fuzz.token_set_ratio(car_model_norm, target_norm),
						fuzz.token_set_ratio(car_make_norm, target_norm),
					)

					if tier == 2 and family_score < HARSH_FUZZY_THRESHOLD:
						continue

					scored.append({**item, "score": family_score, "_tier": tier})

				scored.sort(key=lambda x: (x["_tier"], -x.get("price", 0)))
				ranked_filtered = scored[:15]

			elif model_local or make_local:
				ranked_filtered = rank_filtered(filtered, model_local, make_local, top_n=15)

			elif diversify:
				ranked_filtered = diversify_by_model(filtered, max_total=15)

			else:
				ranked_filtered = filtered[:15]

			# If the harsh filter wiped everything out, treat as 0 cars
			if not ranked_filtered:
				record(True, { "msg": "no cars passed harsh filter" })
				return {
					"success": True,
					"message": "sorry, no cars found for the given preferences.",
					"data": [],
					"count": 0,
					"count_in_words": num2words(0, lang='en_IN')
				}

			record(True)
			final_result = []
			for car in ranked_filtered:
				price_raw = car.get("price", 0)
				price = num2words(round(price_raw, -3), lang='en_IN')
				mileage = num2words(round(car.get("mileage", 0), -3), lang='en_IN')
				discount = car.get("discount", {})
				discount_value = discount.get("value", 0)
				hub = car.get("hub", "")
				hub_info = get_hub_location(car.get("hub_id", 0))
				if hub_info is not None:
					hub = hub_info.get("pronounce_name", hub)

				# ── Segment assignment ────────────────────────────────────────────────
				car_make_raw  = car.get("make", "")
				car_model_raw = car.get("model", "")
				car_segment = await get_car_segment(
					make=car_make_raw,
					model=car_model_raw,
					price_rupees=price_raw,
					body_type=car.get("body_type", ""),
					similar_cars_dict=SIMILAR_CARS,
				)
				# ─────────────────────────────────────────────────────────────────────

				new_car = {
					"car_lead_id": car.get("id", ""),
					"make_year": year_to_words(car.get("registration_year", 0), dial_info.get("default_language", "en")),
					"make": convert_to_words(car_make_raw),
					"model": convert_to_words(car_model_raw.replace("Dzire", "डिज़ायर")),
					"variant": convert_to_words(car.get("variant", "")),
					"km_driven": mileage,
					"fuel_type": car.get("fuel_type", ""),
					"body_type": car.get("body_type", ""),
					"transmission": car.get("transmission", ""),
					"city": car.get("city", ""),
					"price": price,
					"perks": car.get("perks", ""),
					"color": car.get("color", ""),
					"hub": hub,
					"hub_id": car.get("hub_id", ""),
					"rto": car.get("rto", ""),
					"no_of_owners": car.get("no_of_owners", 0),
					"discount_value": num2words(round(discount_value, -3), lang='en_IN') if discount_value > 0 else "no discount",
					"segment": car_segment,   # ← new field
				}
				if discount_value > 0:
					discount_start_time = iso_to_human(discount.get("start_time", now_ist.isoformat()))
					discount_end_time = iso_to_human(discount.get("end_time", now_ist.isoformat()))
					new_car.update({
						"discount_start_time": f"{discount_start_time.get('date')} {discount_start_time.get('month')}",
						"discount_end_time": f"{discount_end_time.get('date')} {discount_end_time.get('month')}",
						"price_after_discount": num2words(round(discount.get("final_discounted_price", price_raw), -3), lang='en_IN')
					})
				final_result.append(new_car)
			logger.info(f"Returning from {function_name}: {final_result}")

			if function_name != "get_number_of_cars_in_a_city":
				job_ctx.proc.userdata["last_fetched"] = final_result
				ALLOWED_KEYS = {"car_lead_id", "make", "model", "variant", "price", "make_year", "fuel_type", "transmission", "city", "color", "km_driven", "segment"}
				existing = job_ctx.proc.userdata.setdefault("prefetch_output", {}).setdefault("fetched_cars", [])
				seen_ids = {x.get("car_lead_id") for x in existing if isinstance(x, dict)}
				for item in final_result:
					car_lead_id = item.get("car_lead_id")
					if car_lead_id and car_lead_id not in seen_ids:
						existing.append({k: item[k] for k in ALLOWED_KEYS if k in item})
						seen_ids.add(car_lead_id)

			existing_prefs = job_ctx.proc.userdata.setdefault("additional_user_preferences", [])
			existing_prefs_str = ", ".join(existing_prefs)
			if existing_prefs_str:
				existing_prefs_str = (
					f"User has also mentioned these additional preferences: {existing_prefs_str}. "
					f"Consider these preferences when pitching the cars, and if possible, try to find cars that take care of these additional preferences as well. "
				)

			used_standard_fuzzy = not (prefer_model or prefer_make) and (model_local or make_local) and function_name != "check_model_availability"
			if used_standard_fuzzy and ranked_filtered[0].get("score", 100) < 30:
				message = "The system couldn't find an exact match for the model the user mentioned. "
				logger.info(f"Returning due to low score {ranked_filtered[0].get('score', 0)} {additional_message} {message}")
				return {
					"success": False,
					"message": additional_message + message,
					"data": [],
					"count": 0,
					"count_in_words": "zero"
				}

			if model_local and (model_local in ranked_filtered[0]["model"].lower() or ranked_filtered[0]["model"].lower() in model_local):
				message = (
					f'[SYSTEM INSTRUCTION - DO NOT READ ALOUD] Cars found:  {"काफ़ी" if filtered_count > 10 else filtered_count} cars matching the users request. {existing_prefs_str}'
				)
			else:
				message = (
					f'[SYSTEM INSTRUCTION - DO NOT READ ALOUD] Cars found: {"काफ़ी" if filtered_count > 10 else filtered_count} cars matching the users request. {existing_prefs_str}.'
				)

			logger.info(f"Message to return for {function_name}: {message}")

			# ── Segment split ─────────────────────────────────────────────────────
			cars_to_pitch, cars_to_suggest = await split_cars_by_role(final_result)
			# ─────────────────────────────────────────────────────────────────────

			return {
				"success": True,
				"message": additional_message + message,
				"existing_prefs_str": existing_prefs_str,
				"additional_message": additional_message,
				"data": final_result,
				"cars_to_pitch": cars_to_pitch,
				"cars_to_suggest": cars_to_suggest,
				"count": filtered_count,
				"count_in_words": count
			}

		record(False, resp.json())
		return {
			"success": False,
			"message": "Failed to get cars for the given preferences",
			"data": [],
		}

	# ──────────────────────────────────────────────────────────────────────────
	# Build payload
	# ──────────────────────────────────────────────────────────────────────────
	pitched_cars_lead_ids = pitched_cars_lead_ids or []
	additional_user_preferences = additional_user_preferences or []

	job_ctx = get_job_context()
	existing_pitched = job_ctx.proc.userdata.setdefault("pitched_cars_lead_ids", [])
	existing_prefs = job_ctx.proc.userdata.setdefault("additional_user_preferences", [])
	job_ctx.proc.userdata["pitched_cars_lead_ids"] = list(set(existing_pitched + pitched_cars_lead_ids))
	job_ctx.proc.userdata["additional_user_preferences"] = list(set(existing_prefs + additional_user_preferences))
	all_pitched = job_ctx.proc.userdata["pitched_cars_lead_ids"]
	all_prefs = job_ctx.proc.userdata["additional_user_preferences"]

	payload = {
		"make": make.lower(),
		"model": model.lower(),
		"city": city.lower(),
		"fuel_type": fuel_type.lower(),
		"max_price": max_price,
		"transmission": transmission.lower(),
		"body_type": body_type.lower(),
		"min_year": min_year,
		"max_mileage": max_km_driven,
		"rto": rto.lower(),
		"color": get_colors_for_filter(color.lower()),
		"seats": get_seating_capacity_for_filter(seating_capacity),
		"pitched_cars_lead_ids": all_pitched,
		"additional_preferences": all_prefs
	}
	payload = {k: v for k, v in payload.items() if v}
	if hub_id and hub_id > 0:
		hub_info = get_hub_location(hub_id)
		if hub_info is not None:
			hub_keyword = hub_info.get("search_keyword", None)
			if hub_keyword is not None:
				payload.update({"hub": hub_keyword})

	# ──────────────────────────────────────────────────────────────────────────
	# Expand model/make via ALMOST_SIMILAR_CAR grid
	# ──────────────────────────────────────────────────────────────────────────
	expanded_model, original_model_norm = expand_almost_similar(payload.get("model", ""))
	expanded_make, original_make_norm = expand_almost_similar(payload.get("make", ""))
	if expanded_model:
		payload["model"] = expanded_model
	if expanded_make:
		payload["make"] = expanded_make

	prefer_kwargs = {
		"prefer_model": original_model_norm or "",
		"prefer_make": original_make_norm or "",
	}

	should_diversify = not payload.get("make") and not payload.get("model")

	# ──────────────────────────────────────────────────────────────────────────
	# Geocode → nearest-hub bias
	# ──────────────────────────────────────────────────────────────────────────
	hub_keywords_str = ""
	if not hub_id and payload.get("city", "") in ["bangalore", "chennai", "delhi", "delhi-ncr", "ghaziabad", "hyderabad", "mumbai", "pune"] and area_or_locality:
		async def find_nearest_hubs(city: str, locality: str) -> dict:
			api_key = "AIzaSyAd9g4_ufJJNOW6qqRbcDspsS3AX9NopO8"
			address = f"{locality} {city}".strip()
			url = "https://maps.googleapis.com/maps/api/geocode/json"
			params = {"address": address, "key": api_key}

			async def _geocode():
				for attempt in range(3):
					try:
						async with httpx.AsyncClient(timeout=10.0) as client:
							resp = await client.get(url, params=params)
						if resp.status_code != 200:
							logger.warning("Geocode request returned status %s (attempt %s).", resp.status_code, attempt + 1)
							await asyncio.sleep(1)
							continue
						data = resp.json()
						status = data.get("status")
						if status != "OK":
							if status == "ZERO_RESULTS":
								return {"error": True, "message": "Address could not be geocoded (no results)."}
							return {"error": True, "message": f"Geocoding failed: {status}"}
						results = data.get("results", [])
						if not results:
							return {"error": True, "message": "No geocoding results returned."}
						loc = results[0].get("geometry", {}).get("location")
						if not loc or "lat" not in loc or "lng" not in loc:
							return {"error": True, "message": "Geocoding response missing location."}
						return {"error": False, "lat": float(loc["lat"]), "lng": float(loc["lng"])}
					except httpx.RequestError:
						logger.exception("HTTP error while calling Geocoding API (attempt %s).", attempt + 1)
						await asyncio.sleep(1)
						continue
					except Exception:
						logger.exception("Unexpected error while geocoding (attempt %s).", attempt + 1)
						await asyncio.sleep(1)
						continue
				return {"error": True, "message": "Failed to geocode address after multiple attempts."}

			geocode_result = await _geocode()
			if geocode_result.get("error"):
				return {"status": "error", "message": geocode_result.get("message", "Geocoding failed.")}
			user_lat = geocode_result["lat"]
			user_lng = geocode_result["lng"]

			def _haversine(lat1, lon1, lat2, lon2):
				R = 6371.0
				dlat = radians(lat2 - lat1)
				dlon = radians(lon2 - lon1)
				a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
				c = 2 * asin(sqrt(a))
				return R * c

			city_key = city.strip().lower()
			matched = []
			for hub in hubs_with_location:
				tags = hub.get("city_tags", []) or []
				if any(city_key == t.lower() for t in tags):
					matched.append(hub)
			if not matched:
				matched = list(hubs_with_location)
			hubs_with_dist = []
			for hub in matched:
				try:
					hlat = float(hub.get("lat"))
					hlng = float(hub.get("long") or hub.get("lng") or 0)
				except Exception:
					continue
				dist_km = _haversine(user_lat, user_lng, hlat, hlng)
				hub_copy = dict(hub)
				hub_copy["distance_km"] = round(dist_km, 3)
				hubs_with_dist.append(hub_copy)
			if not hubs_with_dist:
				return {"status": "error", "message": "No hubs with valid coordinates available."}
			hubs_with_dist.sort(key=lambda x: x["distance_km"])
			nearest = hubs_with_dist[:3]
			return {"status": "success", "hubs": nearest}

		hubs_result = await find_nearest_hubs(payload.get("city", ""), area_or_locality)
		if hubs_result.get("status") == "success":
			nearest_hubs = hubs_result.get("hubs", [])
			if nearest_hubs:
				hub_keywords = [h.get("search_keyword", "") for h in nearest_hubs]
				if hub_keywords:
					hub_keywords_str = ",".join(hub_keywords)

	# ──────────────────────────────────────────────────────────────────────────
	# Primary search
	# ──────────────────────────────────────────────────────────────────────────
	if hub_keywords_str:
		nearest_hubs_primary_result = await return_cars(
			ctx, {**payload, "hub": hub_keywords_str},
			"get_cars_according_to_user_specifications",
			diversify=should_diversify, **prefer_kwargs,
		)
	else:
		nearest_hubs_primary_result = {"count": 0, "data": []}

	if nearest_hubs_primary_result.get("count", 0) > 10:
		primary_result = nearest_hubs_primary_result
	else:
		basic_primary_result = await return_cars(
			ctx, {**payload},
			"get_cars_according_to_user_specifications",
			diversify=should_diversify, **prefer_kwargs,
		)
		if basic_primary_result.get("count", 0):
			all_data = basic_primary_result.get("data", []) + nearest_hubs_primary_result.get("data", [])
			unique_data = list({item.get("car_lead_id"): item for item in all_data}.values())
			# Re-split after merging so pitch/suggest counts are accurate
			merged_pitch, merged_suggest = await split_cars_by_role(unique_data)
			primary_result = {
				**basic_primary_result,
				"data": unique_data,
				"cars_to_pitch": merged_pitch,
				"cars_to_suggest": merged_suggest,
				"count": len(unique_data),
			}
		else:
			primary_result = basic_primary_result

	primary_cars_count = primary_result.get("count", 0)
	excluded_keys = {
		"pitched_cars_lead_ids",
		"additional_preferences",
		"city",
		"max_price",
	}
	primary_preferences = [k for k in payload if k not in excluded_keys]
	primary_preferences_count = len(primary_preferences)
	if primary_preferences_count == 2 and "make" in primary_preferences and "model" in primary_preferences:
		primary_preferences = ["model"]
		primary_preferences_count = 1

	# ──────────────────────────────────────────────────────────────────────────
	# CASE 1: > 10 cars → ask another preference question
	# ──────────────────────────────────────────────────────────────────────────
	if primary_cars_count > 10:
		return {
			"next_action": (
				"There are many cars available matching the user's preferences. To narrow down the options, "
				"ask the user the next preference question that has not been asked. Do not mention that we want to narrow down cars. "
				"Once the user provides this additional preference, use it to filter the cars further and return "
				"the updated list of cars using get_cars_according_to_user_specifications function. "
				"If ALL preference questions have already been asked, start pitching cars"
			),
			**primary_result
		}

	# Pre-compute "slightly over budget" pool for CASE 2 and CASE 3
	next_budget_count = 0
	next_budget_result = {"count": 0, "data": []}
	has_budget = max_price > 0
	if has_budget:
		next_budget_result = await return_cars(
			ctx, {**payload, "min_price": max_price, "max_price": 1.1 * max_price},
			"get_cars_according_to_user_choice_with_extra_budget",
			**prefer_kwargs,
		)
		next_budget_count = next_budget_result.get("count", 0)

	# ──────────────────────────────────────────────────────────────────────────
	# CASE 2: 1–10 cars → split and pitch
	# ──────────────────────────────────────────────────────────────────────────
	if primary_cars_count > 0:
		pitch_list   = primary_result.get("cars_to_pitch",   primary_result.get("data", []))
		suggest_list = primary_result.get("cars_to_suggest", [])
		pitch_count   = len(pitch_list)
		suggest_count = len(suggest_list)

		if next_budget_count:
			ext_pitch   = next_budget_result.get("cars_to_pitch",   next_budget_result.get("data", []))
			ext_suggest = next_budget_result.get("cars_to_suggest", [])
			return {
				"next_action": (
					f"Found {pitch_count} car(s) to PITCH within budget "
					f"(segments: {', '.join(sorted(set(c.get('segment','?') for c in pitch_list)))}) "
					f"and {suggest_count} car(s) to SUGGEST as upgrades. "
					f"Additionally found {next_budget_count} car(s) in the slightly extended budget range. "
					f"Pitch the cars_to_pitch list first. "
					f"Only mention cars_to_suggest when the user asks for upgrade options or nothing from pitch suits them. "
					f"If only one car is within budget pitch it and also introduce one car from extended budget as an option."
				),
				"cars_to_pitch": pitch_list,
				"cars_to_suggest": suggest_list,
				"cars_in_extended_budget": {
					"existing_prefs_str": next_budget_result.get("existing_prefs_str", ""),
					"additional_message": next_budget_result.get("additional_message", ""),
					"cars_to_pitch":   ext_pitch,
					"cars_to_suggest": ext_suggest,
					"data": next_budget_result.get("data", []),
				},
			}

		return {
			"next_action": (
				f"Pitch the {pitch_count} car(s) in cars_to_pitch "
				f"(segments: {', '.join(sorted(set(c.get('segment','?') for c in pitch_list))) or 'mixed'}). "
				f"{'Mention cars_to_suggest only if user asks for something better or pricier — do not pitch them.' if suggest_list else ''}"
			),
			"cars_to_pitch":   pitch_list,
			"cars_to_suggest": suggest_list,
			"existing_prefs_str": primary_result.get("existing_prefs_str", ""),
			"additional_message": primary_result.get("additional_message", ""),
		}

	# ──────────────────────────────────────────────────────────────────────────
	# CASE 3: 0 cars → phased relaxation
	# ──────────────────────────────────────────────────────────────────────────
	if next_budget_count:
		ext_pitch   = next_budget_result.get("cars_to_pitch",   next_budget_result.get("data", []))
		ext_suggest = next_budget_result.get("cars_to_suggest", [])
		return {
			"next_action": "pitch available cars",
			"cars_to_pitch":   ext_pitch,
			"cars_to_suggest": ext_suggest,
			**next_budget_result,
		}

	# Special case: no preferences at all → just try a budget relax
	if primary_preferences_count == 0:
		if not has_budget:
			return primary_result
		relaxed_budget_only = await return_cars(
			ctx, {**payload, "max_price": 0},
			"get_cars_according_to_user_choice_with_extra_budget",
			**prefer_kwargs,
		)
		if relaxed_budget_only.get("count", 0) > 0:
			rb_pitch   = relaxed_budget_only.get("cars_to_pitch",   relaxed_budget_only.get("data", []))
			rb_suggest = relaxed_budget_only.get("cars_to_suggest", [])
			return {
				"next_action": (
					f"No cars found matching the user's specifications. "
					f"However, found {relaxed_budget_only.get('count', 0)} cars when we relax the budget constraint. "
					f"Lowest priced car starts from {relaxed_budget_only['data'][0]['price']}. "
					f"Would you like to see cars in this range? If user says yes, pitch from cars_to_pitch first."
				),
				"cars_to_pitch":   rb_pitch,
				"cars_to_suggest": rb_suggest,
				"cars_in_extended_budget": {
					"existing_prefs_str": relaxed_budget_only.get("existing_prefs_str", ""),
					"additional_message": relaxed_budget_only.get("additional_message", ""),
					"data": relaxed_budget_only.get("data", []),
				},
			}
		return primary_result

	# ──────────────────────────────────────────────────────────────────────────
	# Phased drop order
	# Phase 1:  drop ['hub','hub_id','rto','min_year','color','max_mileage']
	# Phase 2:  Advisor fallback — check model at any price (report starting
	#           price if over-budget) + find same-segment peers within budget
	# Phase 3a: drop model entirely
	# Phase 3b: drop make, owner, fuel_type, transmission, seats, body_type, max_price
	# ──────────────────────────────────────────────────────────────────────────
	PHASE_1_KEYS = ["hub", "hub_id", "rto", "min_year", "color", "max_mileage"]
	PHASE_3_KEYS = ["make", "owner", "fuel_type", "transmission", "seats", "body_type", "max_price"]

	relaxed_payload = {**payload}
	dropped_keys = []

	def _relaxed_response(retry_result, dropped):
		pretty_drops = ", ".join(dropped) if len(dropped) <= 2 else "कुछ"
		r_pitch   = retry_result.get("cars_to_pitch",   retry_result.get("data", []))
		r_suggest = retry_result.get("cars_to_suggest", [])
		return {
			"next_action": (
				f"No cars found matching all of the user's specifications. "
				f"However, found {retry_result.get('count', 0)} cars after relaxing the following preferences: {', '.join(dropped)}. "
				f"If we relax some constraints like {pretty_drops} then "
				f"{'many' if retry_result.get('count', 0) > 10 else retry_result.get('count', 0)} options are available. "
				f"can we see them?"
			),
			"cars_to_pitch":   r_pitch,
			"cars_to_suggest": r_suggest,
			"cars_with_relaxed_preferences": {
				"existing_prefs_str": retry_result.get("existing_prefs_str", ""),
				"additional_message": retry_result.get("additional_message", ""),
				"data": retry_result.get("data", []),
			},
		}

	# ── Phase 1 ───────────────────────────────────────────────────────────────
	for key in PHASE_1_KEYS:
		if key not in relaxed_payload:
			continue
		dropped_keys.append(key)
		del relaxed_payload[key]
		retry = await return_cars(
			ctx, {**relaxed_payload},
			"get_cars_with_relaxed_preferences",
			**prefer_kwargs,
		)
		if retry.get("count", 0) > 0:
			return _relaxed_response(retry, dropped_keys)

	# ── Phase 2: Advisor fallback — model over-budget or unavailable ──────────
	if "model" in primary_preferences:
		lookup_make = original_make_norm or payload.get("make", "")
		lookup_model = original_model_norm or payload.get("model", "")
		make_model_str = f"{lookup_make} {lookup_model}".strip()

		# ── 2a: Check if requested model exists at ANY price (no budget cap) ──
		# The "with_extra_budget" function name causes ascending price sort, so
		# data[0] will be the cheapest listing → the model's starting price.
		model_at_any_price = None
		if has_budget:
			model_at_any_price = await return_cars(
				ctx, {**relaxed_payload, "max_price": 0},
				"get_cars_according_to_user_choice_with_extra_budget",
				**prefer_kwargs,
			)
		model_found_above_budget = bool(
			model_at_any_price and model_at_any_price.get("count", 0) > 0
		)

		# ── 2b: Find same-segment alternatives within the user's budget ────────
		# Build the peer list from ALL models in SIMILAR_CARS that share the same
		# segment code as the requested model — not just the 3 hardcoded options.
		# This ensures alternatives are grouped by true car segment (a1–d2).
		similar_row = get_similar_cars_row(make_model_str)
		segment_peer_models = []
		requested_segment_code = None
		if similar_row:
			logger.info(f"similar_row {similar_row}")
			requested_segment_code = SEGMENT_CODE_MAP.get(similar_row.get("Segment", ""))
			if requested_segment_code:
				seen_peers: set = set()
				for _key, _row in SIMILAR_CARS.items():
					if SEGMENT_CODE_MAP.get(_row.get("Segment", "")) != requested_segment_code:
						continue
					peer_model = _row.get("Model", "")
					peer_norm = _norm(peer_model)
					if not peer_model or peer_norm == _norm(lookup_model):
						continue
					if peer_norm not in seen_peers:
						segment_peer_models.append(peer_model)
						seen_peers.add(peer_norm)
			if not segment_peer_models:
				# Fallback: use the 3 explicit competitor entries from SIMILAR_CARS
				segment_peer_models = [
					similar_row.get(f"Model Option {letter}", "")
					for letter in ("A", "B", "C")
				]
		segment_peer_models = [m for m in segment_peer_models if m]

		similar_within_budget_result = None
		available_make_models = ""
		if segment_peer_models:
			peer_search = ",".join(
				m.lower().replace(" ", "-") for m in segment_peer_models[:8]
			)
			logger.info(f"Segment peer search for {make_model_str} ({requested_segment_code if similar_row else 'unknown'}): {peer_search}")
			similar_within_budget_result = await return_cars(
				ctx,
				{**relaxed_payload, "model": peer_search, "make": ""},
				"check_model_availability",
			)
			if similar_within_budget_result.get("count", 0) > 0:
				sim_data = similar_within_budget_result.get("data", [])
				available_make_models = ", ".join(
					sorted({f"{i['make']} {i['model']}" for i in sim_data})
				)

		alternatives_exist = bool(
			similar_within_budget_result
			and similar_within_budget_result.get("count", 0) > 0
		)

		# ── 2c: Advisor-style response — all text assembled from fetched data ───
		if model_found_above_budget or alternatives_exist:
			starting_price = (
				model_at_any_price["data"][0]["price"]
				if model_found_above_budget
				else None
			)
			_model_status       = "over_budget" if model_found_above_budget else "not_in_inventory"
			_above_budget_count = model_at_any_price.get("count", 0) if model_found_above_budget else 0
			_alt_count          = similar_within_budget_result.get("count", 0) if alternatives_exist else 0

			# Build next_action entirely from fetched data — no hardcoded phrases.
			action_parts = [
				f"Requested model '{make_model_str}': status = {_model_status}."
			]
			if model_found_above_budget:
				action_parts.append(
					f"{_above_budget_count} listing(s) of '{make_model_str}' exist in inventory "
					f"but are all above the user's budget; cheapest is priced at {starting_price}."
				)
			else:
				action_parts.append(
					f"'{make_model_str}' has no listings in inventory."
				)

			if alternatives_exist:
				alt_segments = sorted({c.get("segment", "") for c in (similar_within_budget_result.get("data") or []) if c.get("segment")})
				action_parts.append(
					f"Found {_alt_count} same-segment alternative(s) within the user's budget "
					f"(segment(s): {', '.join(alt_segments) or 'n/a'}): {available_make_models}."
				)
				action_parts.append(
					"Inform the user of the model's status using the data above, "
					"then offer the available alternatives. "
					"If the user agrees, pitch from cars_to_pitch using the default pitching logic."
				)
			else:
				action_parts.append(
					f"No same-segment alternatives found within the user's budget."
				)
				if model_found_above_budget:
					action_parts.append(
						f"Ask the user if they would like to increase their budget to at least "
						f"{starting_price} to consider '{make_model_str}'. "
						f"If yes, pitch from cars_with_relaxed_budget_to_pitch."
					)

			advisor_context = {
				"requested_model":            make_model_str,
				"model_status":               _model_status,
				"model_listings_above_budget": _above_budget_count,
				"model_starting_price":        starting_price,
				"alternatives_count":          _alt_count,
				"alternatives_summary":        available_make_models,
				"segment_code":                requested_segment_code,
			}

			if model_found_above_budget and alternatives_exist:
				sim_data   = similar_within_budget_result.get("data", [])
				sm_pitch   = similar_within_budget_result.get("cars_to_pitch",   sim_data)
				sm_suggest = similar_within_budget_result.get("cars_to_suggest", [])
				rb_data    = model_at_any_price.get("data", [])
				rb_pitch   = model_at_any_price.get("cars_to_pitch",   rb_data)
				rb_suggest = model_at_any_price.get("cars_to_suggest", [])
				return {
					"next_action":   " ".join(action_parts),
					"advisor_context": advisor_context,
					"cars_to_pitch":   sm_pitch,
					"cars_to_suggest": sm_suggest,
					"cars_with_relaxed_budget_to_pitch":   rb_pitch,
					"cars_with_relaxed_budget_to_suggest": rb_suggest,
					"similar_model_cars_within_user_budget": {
						"existing_prefs_str": similar_within_budget_result.get("existing_prefs_str", ""),
						"additional_message": similar_within_budget_result.get("additional_message", ""),
						"data": sim_data,
					},
					"cars_with_relaxed_budget": {
						"existing_prefs_str": model_at_any_price.get("existing_prefs_str", ""),
						"additional_message": model_at_any_price.get("additional_message", ""),
						"data": rb_data,
					},
				}

			if model_found_above_budget and not alternatives_exist:
				rb_data    = model_at_any_price.get("data", [])
				rb_pitch   = model_at_any_price.get("cars_to_pitch",   rb_data)
				rb_suggest = model_at_any_price.get("cars_to_suggest", [])
				return {
					"next_action":   " ".join(action_parts),
					"advisor_context": advisor_context,
					"cars_with_relaxed_budget_to_pitch":   rb_pitch,
					"cars_with_relaxed_budget_to_suggest": rb_suggest,
					"cars_with_relaxed_budget": {
						"existing_prefs_str": model_at_any_price.get("existing_prefs_str", ""),
						"additional_message": model_at_any_price.get("additional_message", ""),
						"data": rb_data,
					},
				}

			# Model not in inventory, but same-segment peers exist within budget.
			sim_data   = similar_within_budget_result.get("data", [])
			sm_pitch   = similar_within_budget_result.get("cars_to_pitch",   sim_data)
			sm_suggest = similar_within_budget_result.get("cars_to_suggest", [])
			return {
				"next_action":   " ".join(action_parts),
				"advisor_context": advisor_context,
				"cars_to_pitch":   sm_pitch,
				"cars_to_suggest": sm_suggest,
				"similar_model_cars_within_user_budget": {
					"existing_prefs_str": similar_within_budget_result.get("existing_prefs_str", ""),
					"additional_message": similar_within_budget_result.get("additional_message", ""),
					"data": sim_data,
				},
			}
		# Neither the model nor any same-segment peer was found → Phase 3a

	# ── Phase 3a: drop model entirely ─────────────────────────────────────────
	if "model" in relaxed_payload:
		dropped_keys.append("model")
		del relaxed_payload["model"]
		retry = await return_cars(
			ctx, {**relaxed_payload},
			"get_cars_with_relaxed_preferences",
		)
		if retry.get("count", 0) > 0:
			return _relaxed_response(retry, dropped_keys)

	# ── Phase 3b ──────────────────────────────────────────────────────────────
	for key in PHASE_3_KEYS:
		if key not in relaxed_payload:
			continue
		dropped_keys.append(key)
		del relaxed_payload[key]
		function_name_for_drop = (
			"get_cars_according_to_user_choice_with_extra_budget"
			if key == "max_price"
			else "get_cars_with_relaxed_preferences"
		)
		retry = await return_cars(
			ctx, {**relaxed_payload}, function_name_for_drop,
		)
		if retry.get("count", 0) > 0:
			return _relaxed_response(retry, dropped_keys)

	# ── Nothing found at all ──────────────────────────────────────────────────
	return {
		"next_action": (
			"No cars found even after relaxing all preferences. "
			"Apologize to the user and suggest they try with a different city or check back later."
		),
		"count": 0,
		"data": []
	}
