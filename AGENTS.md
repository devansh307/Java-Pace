# AGENTS.md

Guidance for AI agents and developers working in the Java-Pace repository.

## Repository overview

Java-Pace holds **Python snippets** for a Spinny (India) used-car **voice bot**: car inventory search and segment-based PITCH/SUGGEST logic. Despite the name, there is no Java code here.

| Branch | Contents |
|--------|----------|
| `main` | README only |
| `cursor/car-segment-voicebot-7321` | `car_segments.py`, `voice_bot_integration.py` (integration patch guide) |
| `cursor/car-segment-bifurcation-8004` | `get_cars_according_to_user_specifications.py` (async Spinny API car search) |

The full voice-bot application (LiveKit Agents runtime, `utils/`, agent entry point) is **not in this repo**.

## Cursor Cloud specific instructions

### What you can run locally

1. **Car segment classification** (standalone, no external services):
   ```bash
   git checkout cursor/car-segment-voicebot-7321
   pip install -r requirements.txt
   python -c "from car_segments import get_car_segment_info, get_segment_for_budget; print(get_car_segment_info('Hyundai', 'Creta', 1_500_000, {})); print(get_segment_for_budget(1_200_000))"
   ```

2. **Full car-search function** (`get_cars_according_to_user_specifications.py` on `cursor/car-segment-bifurcation-8004`) **cannot run** from this repo alone. It requires `utils.city_wise_hubs`, `utils.helpers`, and a LiveKit Agents `RunContext`.

3. **End-to-end voice bot** requires the parent Spinny/LiveKit project plus Spinny Listing API, LLM, STT/TTS, and optionally telephony.

### Lint / test / syntax checks

There is no configured linter or test suite. Useful checks:

```bash
pip install -r requirements.txt
git checkout cursor/car-segment-voicebot-7321
python -m py_compile car_segments.py voice_bot_integration.py

git checkout cursor/car-segment-bifurcation-8004
python -m py_compile get_cars_according_to_user_specifications.py
```

Note: `py_compile` on the bifurcation module succeeds for syntax only; imports will fail at runtime without the parent `utils` package.

### Branch workflow

Check out the feature branch that matches your task before editing or running module code. `main` is intentionally minimal.

### Services (reference)

| Service | Required for E2E voice bot | In this repo |
|---------|---------------------------|--------------|
| Parent voice-bot runtime (LiveKit Agents) | Yes | No |
| Spinny Listing API | Yes | External HTTP |
| `utils/` package | Yes | No |
| LLM / STT / TTS | Yes (voice) | No |
| `car_segments.py` logic | Partial testing | Yes (voicebot branch) |
