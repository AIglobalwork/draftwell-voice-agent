# Draftwell voice agent: rules for the coding agent

Draftwell is a fictional Atlanta duct-cleaning company. This is a portfolio project. The author is learning agentic coding, so keep code simple enough to explain in an interview. No extra abstractions.

## Rules

- Run `uv run pytest -m 'not llm'` (in `agent/`) before every commit.
- Business logic goes in plain modules. Tools in `agent.py` stay thin.
- Arithmetic only in code. The model never calculates prices.
- Never commit secrets. `.env*` is ignored except `.env.example`.
- Repo docs, code comments and README are in English.

## Global Constraints

- Budget: $0. Voice runs on LiveKit Inference credits of the Build plan: $2.50/month (~50 voice minutes), hard cap, no overage charges. Voice is used only for manual checks (changed 2026-11-23: no demo video). Reserve $5-10 stays for an emergency (e.g. Google billing to unlock Live models).
- Voice model (spike result 2026-11-19): Gemini Live is not available for the author's AI Studio key (Google plugin -> HTTP 404), so the Google plugin is NOT used for voice. Voice goes through LiveKit Inference exactly as in the working spike: `inference.RealtimeModel(model=..., voice="Puck")`, ai-coustics noise cancellation (`ai_coustics.audio_enhancement(model=ai_coustics.EnhancerModel.QUAIL_VF_S)`). The model name lives in one env value, `VOICE_MODEL` (default `google/gemini-3.8-live`), so it can be swapped later.
- Conversation tests (marker `llm`) use a Gemini text model through the AI Studio key (`GOOGLE_API_KEY`, free tier), never LiveKit Inference, so they spend no voice credits. Model name in `TEST_LLM_MODEL` (default `gemini-3.5-flash-lite`). Checked 2026-11-19: `gemini-2.5-flash` is closed to new users (HTTP 404); `gemini-3.5-flash-lite` answered; `gemini-3.8-flash` exists but answered HTTP 503 "high demand", so it is an option once it stops returning 503.
- Double booking: no in-process lock (sessions may run in separate processes). `book_slot` checks the slot is free, creates the event, then re-reads the slot's events. If the slot holds more than one event and ours is not the earliest (by creation time, then event id), it deletes ours and raises `SlotTakenError`.
- Agent language: English. Repo docs, code comments, README: English.
- Company: Draftwell, fictional. Site footer: "Draftwell is a fictional company. This site demonstrates an AI booking assistant." Phone shown: (404) 555-0142.
- Service area: Atlanta, Decatur, Brookhaven, Sandy Springs, Dunwoody, Smyrna (ZIP list in config). Time zone `America/New_York`.
- Prices: system $449 incl. 10 vents; extra vent $35; each additional system $349; dryer vent $129; blower $179 per system; antimicrobial $99 per system. Every system includes 10 vents, so extra vents = vents - 10 x systems (never negative).
- Vents unknown: <=1500 sq ft -> 10, <=2500 -> 14, larger -> 18; the quote is then called approximate.
- Every price the agent says is an estimate: "the technician confirms the final price on site".
- Schedule: one crew, Mon-Sat, slots 08:00-12:00 and 13:00-17:00 local, bookable from tomorrow (local date) to 14 days ahead.
- Arithmetic only in code. `book_appointment` recomputes the quote from its own arguments; it never accepts a total from the model.
- SMS code exists but is off: `SMS_ENABLED=false`. Customer email is optional.
- Owner notifications: email and Slack. A failed notification never cancels a booking.
- Public demo limits (sized to ~50 min/month of voice): dedicated demo calendar, call max 300 s. No daily session limit. The README and the site say the live demo has a small monthly voice budget. When the monthly credits are exhausted (the agent does not answer), the site says the live demo is paused and points to the GitHub repository. (Changed 2026-11-23: no video; the README's screenshots and a real call transcript are the proof.)
- The agent introduces itself as a virtual assistant.
- Out of scope: rescheduling, cancelling, mold/repair advice ("the technician will assess on site"), other languages, fake reviews.
- Secrets never committed: `.env*` (except `.env.example`) in `.gitignore`; service account JSON passed as env var `GOOGLE_SERVICE_ACCOUNT_JSON`, never a file in the repo.
- Priority rule: if the end-to-end booking flow (call -> calendar event -> notifications) is not working by the end of day 5, the website shrinks to hero + call button + panel.
