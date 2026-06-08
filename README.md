# Java-Pace

Reference implementation for advisor-style used-car recommendation fallbacks.

## Car advisor fallback helper

`src/car_advisor/fallbacks.py` contains a dependency-free helper that can be
called after inventory has been fetched:

- exact requested model within budget: return those cars first
- requested model available only above budget: mention its starting price
- requested model unavailable: suggest same-segment alternatives
- requested model above budget and alternatives exist: return both signals

Example:

```python
from car_advisor import build_advisor_recommendation

result = build_advisor_recommendation(
    inventory_rows,
    requested_model="i20",
    max_budget=5,
)

print(result.message)
```

For an i20 request with a five lakh budget, if i20 starts at six lakh twenty
five thousand and Baleno/Altroz are available in budget, the helper returns:

`i20 current budget mein available nahi hai. i20 ka starting price six lakh twenty five thousand hai. Similar options mein Baleno, Altroz available hain.`
