# Draftwell Voice Booking Agent Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A voice AI agent that answers calls for a fictional Atlanta duct cleaning company (Draftwell), quotes from a price list, books a 4-hour slot in Google Calendar and notifies the customer and the owner, plus the company's one-page website with a "Talk to our AI assistant" button.

**Architecture:** All business logic (pricing, service area, scheduling, booking, notifications) lives in plain, unit-tested Python modules. A thin LiveKit Agents layer exposes that logic to a Gemini Live realtime model (served through LiveKit Inference, model name from `VOICE_MODEL`) as function tools; the model only collects data and calls tools, it never does arithmetic or invents slots. A Next.js site (from LiveKit's `agent-starter-react` template, restyled to design B) connects the browser to the agent and shows a live panel with the "SMS" and owner notification the agent emits.

**Tech Stack:** Python 3.12, uv, `livekit-agents[google]~=1.8`, `livekit-plugins-ai-coustics~=0.3` (noise cancellation, as in the spike); voice via LiveKit Inference (`inference.RealtimeModel(model=VOICE_MODEL, voice="Puck")`, default `google/gemini-3.8-live`); Gemini text model via `google.LLM(model=TEST_LLM_MODEL)` (default `gemini-3.5-flash-lite`) with the AI Studio key, for conversation tests only; google-api-python-client (Calendar), httpx (Slack), smtplib (email), Twilio SDK (SMS, disabled by flag), pytest + pytest-asyncio; Next.js + `@livekit/components-react` (template), Netlify; LiveKit Cloud (Build plan); GitHub Actions.

**Spec:** `docs/superpowers/specs/2026-11-18-duct-voice-agent-design.md` (Ukrainian; Task 1 adds the English copy at `docs/specs/2026-11-18-voice-booking-agent-design.md`). Approved site design: https://claude.ai/artifact/2KjFptJQ1y9STLvXgXHRxh, artboard "B. Service van".

## Global Constraints

- Budget: $0. Voice runs on LiveKit Inference credits of the Build plan: $2.50/month (~50 voice minutes), hard cap, no overage charges. Voice is used only for manual checks and the demo video. Reserve $5–10 stays for an emergency (e.g. Google billing to unlock Live models).
- Voice model (spike result 2026-11-19): Gemini Live is not available for the author's AI Studio key (Google plugin → HTTP 404), so the Google plugin is NOT used for voice. Voice goes through LiveKit Inference exactly as in the working spike: `inference.RealtimeModel(model=..., voice="Puck")`, ai-coustics noise cancellation (`ai_coustics.audio_enhancement(model=ai_coustics.EnhancerModel.QUAIL_VF_S)`). The model name lives in one env value, `VOICE_MODEL` (default `google/gemini-3.8-live`), so it can be swapped later.
- Conversation tests (marker `llm`) use a Gemini text model through the AI Studio key (`GOOGLE_API_KEY`, free tier), never LiveKit Inference, so they spend no voice credits. Model name in `TEST_LLM_MODEL` (default `gemini-3.5-flash-lite`). Checked 2026-11-19: `gemini-2.5-flash` is closed to new users (HTTP 404); `gemini-3.5-flash-lite` answered; `gemini-3.8-flash` exists but answered HTTP 503 "high demand", so it is an option once it stops returning 503.
- Double booking: no in-process lock (sessions may run in separate processes). `book_slot` checks the slot is free, creates the event, then re-reads the slot's events. If the slot holds more than one event and ours is not the earliest (by creation time, then event id), it deletes ours and raises `SlotTakenError`.
- Agent language: English. Repo docs, code comments, README: English.
- Company: Draftwell, fictional. Site footer: "Draftwell is a fictional company. This site demonstrates an AI booking assistant." Phone shown: (404) 555-0142.
- Service area: Atlanta, Decatur, Brookhaven, Sandy Springs, Dunwoody, Smyrna (ZIP list in config). Time zone `America/New_York`.
- Prices: system $449 incl. 10 vents; extra vent $35; each additional system $349; dryer vent $129; blower $179 per system; antimicrobial $99 per system. Plan decision: every system includes 10 vents, so extra vents = vents − 10 × systems (never negative).
- Vents unknown: ≤1500 sq ft → 10, ≤2500 → 14, larger → 18; the quote is then called approximate.
- Every price the agent says is an estimate: "the technician confirms the final price on site".
- Schedule: one crew, Mon–Sat, slots 08:00–12:00 and 13:00–17:00 local, bookable from tomorrow (local date) to 14 days ahead.
- Arithmetic only in code. `book_appointment` recomputes the quote from its own arguments; it never accepts a total from the model.
- SMS code exists but is off: `SMS_ENABLED=false`. Customer email is optional.
- Owner notifications: email and Slack. A failed notification never cancels a booking.
- Public demo limits (sized to ~50 min/month of voice): dedicated demo calendar, call max 300 s. No daily session limit. The README and the site say the live demo has a small monthly voice budget and the video is the main demo. When the monthly credits are exhausted (the agent does not answer), the site says the live demo is paused and points to the video.
- The agent introduces itself as a virtual assistant.
- Out of scope: rescheduling, cancelling, mold/repair advice ("the technician will assess on site"), other languages, fake reviews.
- Secrets never committed: `.env*` (except `.env.example`) in `.gitignore`; service account JSON passed as env var `GOOGLE_SERVICE_ACCOUNT_JSON`, never a file in the repo.
- Priority rule: if Task 7 is not working end to end (call → calendar event → notifications) by the end of day 5, Task 9 shrinks to hero + call button + panel.

## Review Focus

1. Caller changes details after hearing a quote (e.g. 14 vents, then "actually 16") → the booking uses the quote recomputed from the final arguments. Test: Task 6 `test_book_recomputes_quote`.
2. Worker runs in UTC late in the evening ET → "tomorrow" means tomorrow in Atlanta, not in UTC. Test: Task 3 `test_first_slot_is_tomorrow_in_local_time`.
3. ZIP said in odd forms ("30307-1234", "30 307") → normalized before the area check. Test: Task 3 `test_normalize_zip_forms`.
4. Two callers take the same slot → the second gets "slot taken" plus fresh alternatives, never a double booking, even when both pass the free-slot check at the same moment in different processes. Tests: Task 4 `test_book_slot_raises_when_taken`, `test_book_slot_loses_race_deletes_own_event`, `test_book_slot_wins_race_keeps_own_event`, Task 6 `test_book_slot_taken_returns_alternatives`.
5. Slack or SMTP is down → booking stands, the caller still hears it is booked, the failure is logged. Test: Task 5 `test_failed_channel_does_not_raise`.

## Schedule

| Day | Tasks |
|---|---|
| 1 | 0, 1, 2 |
| 2 | 3, 4 |
| 3 | 5, 6 |
| 4 | 7 |
| 5 | 7 (finish, voice test), 8 (deploy agent), start 9 — checkpoint |
| 6 | 9, 10 |
| 7 | 11, buffer |

## File Structure

```
draftwell/
  CLAUDE.md                     # rules for the coding agent
  README.md
  .gitignore  .env.example
  .github/workflows/ci.yml
  docs/specs/…  docs/plans/…
  agent/
    pyproject.toml
    config/pricing.yaml         # owner-editable price list
    config/business.yaml        # schedule, ZIPs, call length limit
    src/draftwell/
      config.py                 # load YAML → frozen dataclasses
      pricing.py                # estimate_vents, calculate_quote
      service_area.py           # normalize_zip, is_in_service_area
      scheduling.py             # Slot, candidate/free/available slots
      calendar_client.py        # CalendarClient protocol + Google impl
      booking.py                # Customer, Booking, book_slot
      notify.py                 # message texts, Notifier (email/Slack/SMS)
      flows.py                  # Deps + tool logic returning text for the model
      agent.py                  # DraftwellAgent: INSTRUCTIONS + thin function tools
      main.py                   # AgentServer entrypoint
    tests/
      fakes.py                  # FakeCalendar, FakeNotifier, recording publish
      test_pricing.py  test_service_area.py  test_scheduling.py
      test_booking.py  test_notify.py  test_flows.py
      test_conversations.py     # LLM tests, marker `llm`
  web/                          # Next.js from agent-starter-react
```

---

### Task 0: Accounts and voice spike (throwaway)

**Files:** none committed. Spike lives outside the repo.

- [x] **Step 1:** Create a Google AI Studio API key. Create a LiveKit Cloud project (Build plan) and install the `lk` CLI.
- [x] **Step 2 (done 2026-11-19):** LiveKit `agent-starter-python` spike in console mode. Google plugin → HTTP 404 (key has no Live models); `inference.RealtimeModel(model="google/gemini-3.8-live", voice="Puck")` → agent answers by voice. `lk cloud auth` failed with 400 on Windows; project added with `lk project add` and API keys instead.
  Expected: you speak, the agent answers by voice. If Gemini returns a region/permission error from Ukraine, stop and pick a paid realtime model from the reserve; record the decision in `docs/specs`.
- [x] **Step 3:** Google Cloud project → enable Calendar API → service account → JSON key. Create a new Google Calendar "Draftwell demo" and share it with the service account email ("Make changes to events"). Note the calendar ID. (IDs and the key file stay outside the repo; values go only into `.env`.)
- [x] **Step 4:** Slack: create a workspace channel + incoming webhook. Gmail: create an app password for SMTP.
  Expected: every value for `.env.example` (Task 1) is known.

### Task 1: Repository skeleton, docs, config loading

**Files:**
- Create: `CLAUDE.md`, `README.md` (stub), `.gitignore`, `.env.example`, `docs/specs/2026-11-18-voice-booking-agent-design.md` (English translation of the spec), `docs/plans/2026-11-18-draftwell-voice-agent.md` (this plan), `agent/pyproject.toml`, `agent/config/pricing.yaml`, `agent/config/business.yaml`, `agent/src/draftwell/__init__.py`, `agent/src/draftwell/config.py`
- Test: `agent/tests/test_config.py`

**Interfaces:**
- Produces:
  - `PriceList(system_base: int, included_vents_per_system: int, extra_vent: int, additional_system: int, dryer_vent: int, blower_per_system: int, antimicrobial_per_system: int, vent_estimates: tuple[VentEstimate, ...])`
  - `VentEstimate(max_sqft: int | None, vents: int)`
  - `BusinessConfig(company_name: str, phone: str, timezone: ZoneInfo, work_days: frozenset[int], slot_starts: tuple[time, ...], slot_hours: int, min_days_ahead: int, max_days_ahead: int, service_zips: frozenset[str], max_call_seconds: int)` (`work_days`: 0 = Monday)
  - `load_price_list(path: Path) -> PriceList`, `load_business_config(path: Path) -> BusinessConfig`

- [x] **Step 1:** `git init`, GitHub repo `draftwell-voice-agent` (already created; private until the author decides otherwise). `.gitignore` includes `.env*`, `!.env.example`, `.superpowers/`, `node_modules/`, `.venv/`, `__pycache__/`.
- [x] **Step 2:** `CLAUDE.md` states: the Global Constraints above; "run `uv run pytest -m 'not llm'` before every commit"; "business logic goes in plain modules, tools in `agent.py` stay thin"; "never commit secrets".
- [x] **Step 3:** `.env.example` keys: `LIVEKIT_URL, LIVEKIT_API_KEY, LIVEKIT_API_SECRET, GOOGLE_API_KEY (AI Studio, free tier; text conversation tests only), VOICE_MODEL (default `google/gemini-3.8-live`), TEST_LLM_MODEL (default `gemini-3.5-flash-lite`; `gemini-3.8-flash` is an option once it stops returning 503), GOOGLE_CALENDAR_ID, GOOGLE_SERVICE_ACCOUNT_JSON, SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, OWNER_EMAIL, SLACK_WEBHOOK_URL, SMS_ENABLED, TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_FROM_NUMBER, OWNER_PHONE`.
- [x] **Step 4:** `pyproject.toml`: deps `livekit-agents[google]~=1.8`, `livekit-plugins-ai-coustics~=0.3`, `google-api-python-client`, `google-auth`, `httpx`, `pyyaml`, `twilio`, `python-dotenv`; dev `pytest`, `pytest-asyncio`; pytest `asyncio_mode = "auto"`, marker `llm`; `[tool.uv] constraint-dependencies = ["yarl<1.24"]` as in the spike (yarl 1.24.1 has no wheel for Python 3.11+).
- [x] **Step 5:** Write `pricing.yaml` and `business.yaml` with the Global Constraints values (`slot_starts: ["08:00", "13:00"]`, `slot_hours: 4`, `work_days: [mon, tue, wed, thu, fri, sat]`, `min_days_ahead: 1`, `max_days_ahead: 14`, `max_call_seconds: 300`, ZIPs for the six cities incl. 30307, 30030, 30319, 30328, 30338, 30080).
- [x] **Step 6: Write the failing test**

```python
def test_loads_real_config_files():
    p = load_price_list(CONFIG / "pricing.yaml")
    assert (p.system_base, p.extra_vent, p.additional_system) == (449, 35, 349)
    assert (p.dryer_vent, p.blower_per_system, p.antimicrobial_per_system) == (129, 179, 99)
    b = load_business_config(CONFIG / "business.yaml")
    assert b.timezone.key == "America/New_York"
    assert b.slot_starts == (time(8), time(13)) and b.slot_hours == 4
    assert 6 not in b.work_days and {"30307", "30030", "30080"} <= b.service_zips
```

- [x] **Step 7:** Run `uv run pytest tests/test_config.py -v` → FAIL (import error).
- [x] **Step 8:** Implement `config.py` (frozen dataclasses, `yaml.safe_load`, day names → ints).
- [x] **Step 9:** Run → PASS. Commit: `chore: project skeleton, docs and config loading`.

### Task 2: Pricing

**Files:** Create `agent/src/draftwell/pricing.py`; Test `agent/tests/test_pricing.py`

**Interfaces:**
- Consumes: `PriceList`
- Produces: `QuoteParams(systems: int, vents: int | None, square_feet: int | None, dryer_vent: bool = False, blower: bool = False, antimicrobial: bool = False)`, `QuoteLine(label: str, amount: int)`, `Quote(lines: tuple[QuoteLine, ...], total: int, vents_estimated: bool)`, `estimate_vents(square_feet: int, prices: PriceList) -> int`, `calculate_quote(params: QuoteParams, prices: PriceList) -> Quote`

- [x] **Step 1: Write the failing tests**

```python
def test_site_example_is_718():            # matches the website and the hero dialog
    q = calculate_quote(QuoteParams(systems=1, vents=14, square_feet=None, dryer_vent=True), PRICES)
    assert [l.amount for l in q.lines] == [449, 140, 129] and q.total == 718
    assert not q.vents_estimated

def test_two_systems_with_all_addons():
    q = calculate_quote(QuoteParams(2, 25, None, blower=True, antimicrobial=True), PRICES)
    assert q.total == 1529                 # 449+349 + 5×35 + 2×179 + 2×99

def test_fewer_vents_than_included_has_no_extra_line():
    q = calculate_quote(QuoteParams(1, 6, None), PRICES)
    assert q.total == 449 and len(q.lines) == 1

@pytest.mark.parametrize("sqft,vents", [(1200, 10), (1500, 10), (1501, 14), (2500, 14), (3800, 18)])
def test_estimate_vents(sqft, vents):
    assert estimate_vents(sqft, PRICES) == vents

def test_square_feet_used_when_vents_unknown():
    q = calculate_quote(QuoteParams(1, None, 2000), PRICES)
    assert q.total == 589 and q.vents_estimated

@pytest.mark.parametrize("params", [QuoteParams(0, 10, None), QuoteParams(1, None, None), QuoteParams(1, 0, None), QuoteParams(1, None, -5)])
def test_invalid_params_raise(params):
    with pytest.raises(ValueError):
        calculate_quote(params, PRICES)
```

- [x] **Step 2:** Run `uv run pytest tests/test_pricing.py -v` → FAIL.
- [x] **Step 3:** Implement. Line labels: `"Whole system, first 10 vents"`, `"Additional system ×N"`, `"N extra vents"`, `"Dryer vent"`, `"Blower ×N"`, `"Antimicrobial ×N"`.
- [x] **Step 4:** Run → PASS. Commit: `feat: price calculation from price list`.

### Task 3: Service area and scheduling

**Files:** Create `service_area.py`, `scheduling.py`; Test `test_service_area.py`, `test_scheduling.py`

**Interfaces:**
- Consumes: `BusinessConfig`
- Produces:
  - `normalize_zip(raw: str) -> str | None` (5 digits or None), `is_in_service_area(raw_zip: str, config: BusinessConfig) -> bool`
  - `Slot(start: datetime, end: datetime)` (frozen, tz-aware, local tz), `Slot.label() -> str` e.g. `"Thu, Dec 3, 8 AM–12 PM"`
  - `candidate_slots(config, now: datetime) -> list[Slot]`
  - `free_slots(candidates: list[Slot], busy: list[tuple[datetime, datetime]]) -> list[Slot]`
  - `first_available(slots: list[Slot], preferred: date | None, limit: int = 3) -> list[Slot]` (slots on `preferred` first; if none that day, the nearest later ones)

- [x] **Step 1: Write the failing tests** (`ET = ZoneInfo("America/New_York")`)

```python
@pytest.mark.parametrize("raw,expected", [("30307", "30307"), ("30307-1234", "30307"), (" 30 307 ", "30307"), ("3030", None), ("abcde", None)])
def test_normalize_zip_forms(raw, expected): assert normalize_zip(raw) == expected

def test_service_area():
    assert is_in_service_area("30030", CFG) and not is_in_service_area("10001", CFG)

def test_first_slot_is_tomorrow_in_local_time():
    now = datetime(2026, 12, 2, 3, 30, tzinfo=UTC)          # Tue Dec 1, 22:30 ET
    assert candidate_slots(CFG, now)[0].start == datetime(2026, 12, 2, 8, tzinfo=ET)

def test_slots_shape_and_window():
    slots = candidate_slots(CFG, datetime(2026, 12, 1, 14, tzinfo=UTC))
    assert {(s.start.hour, s.end.hour) for s in slots} == {(8, 12), (13, 17)}
    assert all(s.start.weekday() != 6 for s in slots)
    assert slots[-1].start.date() == date(2026, 12, 15)

def test_free_slots_removes_only_overlapping():
    slots = candidate_slots(CFG, datetime(2026, 12, 1, 14, tzinfo=UTC))
    busy = [(datetime(2026, 12, 3, 9, tzinfo=ET), datetime(2026, 12, 3, 10, tzinfo=ET))]
    free = free_slots(slots, busy)
    assert datetime(2026, 12, 3, 8, tzinfo=ET) not in [s.start for s in free]
    assert datetime(2026, 12, 3, 13, tzinfo=ET) in [s.start for s in free]

def test_preferred_sunday_returns_next_open_day():
    slots = candidate_slots(CFG, datetime(2026, 12, 1, 14, tzinfo=UTC))
    assert first_available(slots, date(2026, 12, 6))[0].start == datetime(2026, 12, 7, 8, tzinfo=ET)

def test_slot_label():
    assert Slot(datetime(2026, 12, 3, 8, tzinfo=ET), datetime(2026, 12, 3, 12, tzinfo=ET)).label() == "Thu, Dec 3, 8 AM–12 PM"
```

- [x] **Step 2:** Run → FAIL. **Step 3:** Implement (convert `now` to `config.timezone` before taking the date). **Step 4:** Run → PASS.
- [x] **Step 5:** Commit: `feat: service area check and slot scheduling`.

### Task 4: Calendar client and booking

**Files:** Create `calendar_client.py`, `booking.py`, `tests/fakes.py`; Test `test_booking.py`

**Interfaces:**
- Consumes: `Slot`, `candidate_slots`, `Quote`, `BusinessConfig`
- Produces:
  - `CalendarEvent(id: str, created: datetime)` (frozen)
  - `class CalendarClient(Protocol)`: `def busy(self, start: datetime, end: datetime) -> list[tuple[datetime, datetime]]`; `def create_event(self, slot: Slot, summary: str, description: str) -> str` (event id); `def events(self, start: datetime, end: datetime) -> list[CalendarEvent]` (events overlapping the range); `def delete_event(self, event_id: str) -> None`
  - `GoogleCalendarClient(calendar_id: str, service_account_info: dict)` using `freebusy().query`, `events().insert`, `events().list` (`singleEvents=True`, `created` field) and `events().delete`
  - `Customer(name: str, phone: str, address: str, zip_code: str, email: str | None = None)`
  - `Booking(event_id: str, slot: Slot, customer: Customer, quote: Quote)`
  - `class SlotTakenError(Exception)`, `class InvalidSlotError(Exception)`
  - `book_slot(calendar: CalendarClient, config: BusinessConfig, slot_start: datetime, customer: Customer, quote: Quote, now: datetime) -> Booking`
  - `tests/fakes.py`: `FakeCalendar(busy: list | None = None, rival: Literal["before", "after"] | None = None)` with `.events: list[dict]` (each has `id`, `summary`, `description`, `start`, `end`, `created`). `rival` simulates another session that passed the same free-slot check: on `create_event`, the fake also adds an event `"Rival booking"` in the same slot, created 1 s before (`"before"`) or after (`"after"`) ours. `busy()` reports only the constructor's `busy` list, so the pre-check passes.

- [x] **Step 1: Write the failing tests**

```python
def test_book_slot_creates_event():
    cal = FakeCalendar()
    b = book_slot(cal, CFG, datetime(2026, 12, 3, 8, tzinfo=ET), CUSTOMER, QUOTE_718, NOW)
    assert b.slot.end == datetime(2026, 12, 3, 12, tzinfo=ET)
    assert "John Smith" in cal.events[0]["summary"] and "$718" in cal.events[0]["description"]

def test_book_slot_raises_when_taken():
    cal = FakeCalendar(busy=[(datetime(2026, 12, 3, 8, tzinfo=ET), datetime(2026, 12, 3, 12, tzinfo=ET))])
    with pytest.raises(SlotTakenError):
        book_slot(cal, CFG, datetime(2026, 12, 3, 8, tzinfo=ET), CUSTOMER, QUOTE_718, NOW)
    assert cal.events == []

def test_book_slot_loses_race_deletes_own_event():         # another process booked a moment earlier
    cal = FakeCalendar(rival="before")
    with pytest.raises(SlotTakenError):
        book_slot(cal, CFG, datetime(2026, 12, 3, 8, tzinfo=ET), CUSTOMER, QUOTE_718, NOW)
    assert [e["summary"] for e in cal.events] == ["Rival booking"]

def test_book_slot_wins_race_keeps_own_event():           # the other process will delete its own event
    cal = FakeCalendar(rival="after")
    b = book_slot(cal, CFG, datetime(2026, 12, 3, 8, tzinfo=ET), CUSTOMER, QUOTE_718, NOW)
    assert b.event_id in [e["id"] for e in cal.events] and len(cal.events) == 2

@pytest.mark.parametrize("start", [datetime(2026, 12, 3, 9, tzinfo=ET), datetime(2026, 12, 6, 8, tzinfo=ET), datetime(2026, 12, 20, 8, tzinfo=ET)])
def test_book_slot_rejects_invalid_start(start):          # wrong hour, Sunday, beyond 14 days
    with pytest.raises(InvalidSlotError):
        book_slot(FakeCalendar(), CFG, start, CUSTOMER, QUOTE_718, NOW)
```

- [x] **Step 2:** Run → FAIL. **Step 3:** Implement `book_slot`: validate against `candidate_slots`; if `calendar.busy(slot)` is not empty → `SlotTakenError`; create the event; re-read `calendar.events(slot.start, slot.end)`; if there is more than one and ours is not the earliest by `(created, id)`, `delete_event(ours)` and raise `SlotTakenError`. No in-process lock: sessions may run in separate processes; a code comment says why. Event description lists address, phone, email, quote lines and total. Implement `GoogleCalendarClient` (not unit-tested; covered by Step 5).
- [x] **Step 4:** Run → PASS.
- [x] **Step 5:** Manual check: a 5-line script with real `.env` books a slot in "Draftwell demo"; the event appears in Google Calendar; delete it.
- [x] **Step 6:** Commit: `feat: Google Calendar client and slot booking`.

### Task 5: Notifications

**Files:** Create `notify.py`; Test `test_notify.py`

**Interfaces:**
- Consumes: `Booking`, `BusinessConfig`
- Produces:
  - `customer_sms_text(booking: Booking, config: BusinessConfig) -> str`, `owner_booking_text(booking: Booking) -> str`, `owner_message_text(name: str, phone: str, message: str) -> str`
  - `Delivery(channel: Literal["email", "slack", "sms"], status: Literal["sent", "skipped", "failed"], recipient: str)`
  - `Notifier(settings: NotifySettings, senders: Senders | None = None)` (`Senders` holds `email`, `slack`, `sms` async callables; `None` = real senders) with `async confirm_to_customer(booking) -> list[Delivery]` (email if present, SMS if enabled) and `async notify_owner(text: str) -> list[Delivery]` (email + Slack). Channel senders are injectable callables for tests.
  - `NotifySettings.from_env() -> NotifySettings`

- [x] **Step 1: Write the failing tests**

```python
def test_customer_text():
    t = customer_sms_text(BOOKING_718, CFG)
    for part in ["Draftwell", "Thu, Dec 3, 8 AM–12 PM", "$718", "final price", "(404) 555-0142"]:
        assert part in t

def test_owner_booking_text():
    t = owner_booking_text(BOOKING_718)
    for part in ["New booking", "John Smith", "Thu, Dec 3, 8 AM–12 PM", "$718", CUSTOMER.phone, CUSTOMER.address]:
        assert part in t

async def test_sms_skipped_when_disabled():
    n = Notifier(settings(sms_enabled=False), senders=RecordingSenders())
    d = await n.confirm_to_customer(BOOKING_718)
    assert Delivery("sms", "skipped", CUSTOMER.phone) in d

async def test_failed_channel_does_not_raise():
    s = RecordingSenders(slack_raises=True)
    d = await Notifier(settings(), senders=s).notify_owner("New booking …")
    assert {(x.channel, x.status) for x in d} == {("slack", "failed"), ("email", "sent")}
```

- [x] **Step 2:** Run → FAIL. **Step 3:** Implement (SMTP via `asyncio.to_thread(smtplib…)`, Slack via `httpx.AsyncClient.post`, Twilio only when `sms_enabled`). Log failures, never raise.
- [x] **Step 4:** Run → PASS. **Step 5:** Manual: send one real owner notification; it arrives in email and Slack.
- [x] **Step 6:** Commit: `feat: customer and owner notifications`.

### Task 6: Tool flows

**Files:** Create `flows.py`; Test `test_flows.py`

**Interfaces:**
- Consumes: everything above
- Produces:
  - `Deps(prices: PriceList, config: BusinessConfig, calendar: CalendarClient, notifier: Notifier, publish: Callable[[dict], Awaitable[None]], now: Callable[[], datetime])`
  - Panel event dicts published to the browser: `{"type": "sms_to_customer" | "owner_notification", "text": str, "delivered": bool}`
  - `check_area(deps, zip_code: str) -> str`
  - `quote(deps, params: QuoteParams) -> str`
  - `async find_slots(deps, preferred_date: str | None) -> str` (ISO date in, slot labels + ISO starts out; beyond 14 days → says booking is up to 14 days ahead)
  - `async book(deps, slot_start: str, customer: Customer, params: QuoteParams) -> str`
  - `async take_message(deps, name: str, phone: str, message: str) -> str`

- [x] **Step 1: Write the failing tests** (`deps` fixture uses `FakeCalendar`; add `RecordingNotifier` (`.owner_texts`) and `RecordingPublish` (`.events`, async callable) to `tests/fakes.py`)

```python
def test_quote_text_has_lines_total_and_estimate_wording(deps):
    t = quote(deps, QuoteParams(1, 14, None, dryer_vent=True))
    assert "$718" in t and "$140" in t and "estimate" in t.lower() and "final price" in t

async def test_book_recomputes_quote(deps):
    t = await book(deps, "2026-12-03T08:00:00-05:00", CUSTOMER, QuoteParams(1, 16, None, dryer_vent=True))
    assert "$788" in t                                   # 449 + 6×35 + 129, not an earlier $718

async def test_book_publishes_panel_events(deps):
    await book(deps, "2026-12-03T08:00:00-05:00", CUSTOMER, QuoteParams(1, 14, None, dryer_vent=True))
    assert [e["type"] for e in deps.publish.events] == ["sms_to_customer", "owner_notification"]
    assert deps.publish.events[0]["delivered"] is False      # SMS disabled in demo

async def test_book_slot_taken_returns_alternatives(deps_busy_dec3_morning):
    t = await book(deps_busy_dec3_morning, "2026-12-03T08:00:00-05:00", CUSTOMER, QuoteParams(1, 14, None))
    assert "no longer available" in t and "Thu, Dec 3, 1 PM–5 PM" in t

async def test_take_message_notifies_owner(deps):
    t = await take_message(deps, "Mary Lee", "+14045550199", "Call me about a commercial job")
    assert deps.notifier.owner_texts and "Mary Lee" in deps.notifier.owner_texts[0]
    assert deps.publish.events[-1]["type"] == "owner_notification" and "call you back" in t
```

- [x] **Step 2:** Run → FAIL. **Step 3:** Implement; blocking calendar calls via `asyncio.to_thread`. Return texts state facts only and tell the model what to say next (e.g. "Booked. Tell the caller the time window and that a confirmation is on its way.").
- [x] **Step 4:** Run → PASS. Commit: `feat: agent tool flows`.

### Task 7: Voice agent and conversation tests

**Files:** Create `agent.py`, `main.py`; Test `test_conversations.py`

**Interfaces:**
- Consumes: `Deps` and the `flows` functions
- Produces: `DraftwellAgent(deps: Deps)` (subclass of `livekit.agents.Agent`; does NOT set `llm` itself, so tests can run it on a text model; `main.py` passes the voice model to `AgentSession(llm=...)`) with `@function_tool` methods `check_service_area`, `get_quote`, `find_available_slots`, `book_appointment`, `take_message_for_owner`, each a one-line delegation to `flows`; `INSTRUCTIONS: str`; `main.py`: `server = AgentServer()`, `@server.rtc_session(agent_name="draftwell")`, `cli.run_app(server)` (follow the livekit-agents 1.8 Voice AI quickstart for exact entrypoint shape).

- [x] **Step 1:** Write `INSTRUCTIONS`: virtual assistant for Draftwell; collect name, phone, address with ZIP, systems, vents (or square feet), add-ons, preferred day; check ZIP before quoting; prices and times only from tool results; always "estimate, technician confirms the final price on site"; read back details before `book_appointment`; email optional, spelled letter by letter; no mold/repair advice; offer a message for the owner when asked for a person; never agree to discounts.
- [x] **Step 2: Write the failing conversation tests** (marker `llm`; text model `google.LLM(model=os.environ.get("TEST_LLM_MODEL", "gemini-3.5-flash-lite"))` with `GOOGLE_API_KEY` as both session LLM and judge; never LiveKit Inference, so no voice credits are spent; skip the module when `GOOGLE_API_KEY` is not set. `gemini-3.8-flash` is a stronger option via `TEST_LLM_MODEL` once it stops returning 503)

```python
async def test_quote_comes_from_tool():
    r = await session.run(user_input="ZIP 30307. One system, 14 vents and the dryer vent. How much?")
    r.expect.contains_function_call(name="get_quote")
    await r.expect.next_event(type="message").judge(llm, intent="States an estimate of $718 and says the technician confirms the final price on site.")
```

Check `contains_function_call` against the installed livekit-agents version; if it is missing, advance with `r.expect.next_event(type="function_call")` until `get_quote`. Same shape for: `test_unknown_vents_asks_square_feet` (intent: asks for approximate square footage; no `get_quote` yet), `test_out_of_area_zip` (ZIP 10001; `check_service_area` called; intent: says it is outside the area, does not offer a booking), `test_wants_a_person` (intent: offers to take a message for the owner), `test_mold_question` (intent: no diagnosis, technician will assess on site), `test_discount_request` ("Can you do it for $300?"; intent: does not agree to a price outside the price list), `test_slot_taken` (FakeCalendar becomes busy before booking; intent: says the time is gone and offers other times).

- [x] **Step 3:** Run `uv run pytest -m llm -v` → FAIL. **Step 4:** Implement `agent.py`, `main.py`. In `main.py`: build `Deps` from env; `publish` sends JSON via `ctx.room.local_participant.send_text(..., topic="draftwell.panel")`; after `max_call_seconds` (300) say goodbye and end the session; voice model = `inference.RealtimeModel(model=os.environ.get("VOICE_MODEL", "google/gemini-3.8-live"), voice="Puck")` passed to `AgentSession(llm=...)`; noise cancellation as in the spike (`room_io.RoomOptions(audio_input=room_io.AudioInputOptions(noise_cancellation=ai_coustics.audio_enhancement(model=ai_coustics.EnhancerModel.QUAIL_VF_S)))`); check the exact import in the LiveKit docs MCP.
- [x] **Step 5:** Run `-m llm` → PASS (rephrase instructions, not tests, until they pass).
- [x] **Step 6 (passed 2026-11-23):** Voice check in console mode: full booking by voice; event in calendar; email + Slack arrive. This spends the ~50 min monthly voice budget: one or two calls, not a debugging loop (debug with the text tests).
- [x] **Step 7:** Commit: `feat: voice agent with function tools and conversation tests`. **Checkpoint for day 5.**

### Task 8: Deploy the agent to LiveKit Cloud

Moved here from the deploy task so the agent runs in the cloud as soon as it works locally.

**Files:** Create `agent/Dockerfile` (from `lk agent create`), `agent/livekit.toml`

- [x] **Step 1:** Authenticate the `lk` CLI with project API keys, not `lk cloud auth` (it fails with HTTP 400 on Windows): `lk project add` with `--url`, `--api-key`, `--api-secret` from `.env` (the spike already did this), or pass the same global options to each command.
- [x] **Step 2:** `lk agent create` in `agent/`; secrets from `.env` (incl. `GOOGLE_SERVICE_ACCOUNT_JSON`, `VOICE_MODEL`), without `LIVEKIT_URL`/`LIVEKIT_API_KEY`/`LIVEKIT_API_SECRET` (LiveKit Cloud injects them). Expected: agent status running in LiveKit Cloud.
- [x] **Step 3:** One short call to the deployed agent (e.g. LiveKit Agents Playground), with your local agent stopped. Expected: it answers by voice; `lk agent logs` shows the session.
- [x] **Step 4:** Commit: `chore: LiveKit Cloud deploy config`.

### Task 9: Website (design B) with call button and live panel

**Files:** Create `web/` from `agent-starter-react`; Modify its main page, styles, connection-details route; Create `web/components/DemoPanel.tsx`, `web/lib/panel.ts`; Test `web/lib/panel.test.ts`

**Interfaces:**
- Consumes: agent name `draftwell`, panel topic `draftwell.panel`, event shape from Task 6
- Produces: `parsePanelEvent(raw: string) -> PanelEvent | null`

- [ ] **Step 1:** Clone the template into `web/`; set the dispatched agent name to `draftwell` in the connection-details route; `.env.local` with LiveKit keys (not committed).
- [ ] **Step 2:** Rebuild the page from artboard B: header, hero ("Call at 9 pm. Booked by 9:03." + sample dialog), prices with the $718 example, visit steps, area/hours/person, footer. Colors `#0D4A42`, `#F5C518`, `#1C2124`, `#EBEDEC`; fonts Barlow Condensed + Barlow; Atlanta copy and (404) 555-0142. Both "Talk to our AI assistant" buttons start the session. Next to the button: a short note that the live demo has a small monthly voice budget, with a link to the video.
- [ ] **Step 3: Write the failing test**

```ts
test("parses valid panel events and rejects junk", () => {
  expect(parsePanelEvent('{"type":"sms_to_customer","text":"Hi","delivered":false}'))
    .toEqual({ type: "sms_to_customer", text: "Hi", delivered: false });
  expect(parsePanelEvent('{"type":"other"}')).toBeNull();
  expect(parsePanelEvent("not json")).toBeNull();
});
```

- [ ] **Step 4:** Run the web test → FAIL. **Step 5:** Implement `parsePanelEvent` and `DemoPanel` (registers a text stream handler for `draftwell.panel`; shows "Customer's phone" and "Owner's phone" cards; SMS card labelled "Demo: not sent, see README"). **Step 6:** Test → PASS.
- [ ] **Step 7:** Manual: page at 390 px and 1280 px width; keyboard focus visible; a call from the page books a slot and both panel cards appear.
- [ ] **Step 8:** Commit: `feat: Draftwell website with AI call button and demo panel`.

### Task 10: Website deploy and CI

**Files:** Create `.github/workflows/ci.yml`

- [ ] **Step 1:** CI on push: `uv run pytest -m "not llm"` in `agent/`; `npm ci && npm test && npm run build` in `web/`. Push → green.
- [ ] **Step 2:** Import `web/` into Netlify (base directory `web`, build settings in `web/netlify.toml` with the `@netlify/plugin-nextjs` adapter); set `LIVEKIT_URL`, `LIVEKIT_API_KEY`, `LIVEKIT_API_SECRET` (a separate LiveKit key for the site) and `NODE_VERSION=22`. Expected: public URL; with your PC off, a call to the agent deployed in Task 8 books a slot.
  - Changed 2026-11-23: the plan said Vercel, but Vercel blocked the phone verification of the account for 12 hours, so the site went to Netlify (free tier, also runs the token route as a server function).
- [ ] **Step 3:** Commit: `ci: tests and build; Netlify deploy`.

### Task 11: README, video, process write-up

**Files:** Modify `README.md`

- [ ] **Step 1:** README sections: problem (missed calls), 1–2 min video (the main demo), live demo link with a note right next to it: the live demo runs on a small monthly voice budget (~50 minutes), so it may be paused, and the video is the main demo; architecture diagram (from the spec's "where things live"), how to run locally, tests, "Why SMS is simulated" (A2P 10DLC), "How this was built with Claude Code" (spec → plan → tasks, where the agent was wrong and how it was corrected, what you decided yourself), limits of the demo.
- [ ] **Step 2:** Record the video: booking call on the site, panel cards, event in Google Calendar, Slack message.
- [ ] **Step 3:** Fresh-eyes check: clone the repo into a new folder, follow README "run locally" exactly; fix anything that fails.
- [ ] **Step 4:** Commit: `docs: README with demo, architecture and build process`.
