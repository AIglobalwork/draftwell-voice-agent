# Voice booking agent for a duct cleaning company (USA)

> English version of the Ukrainian original: `docs/superpowers/specs/2026-11-18-duct-voice-agent-design.md`.

Design document · 2026-11-18 · status: awaiting approval

## 1. Why this exists

A portfolio project on GitHub that shows the author can work as an AI integrator: embedding AI into real business processes so that customers can book more easily and staff have less routine work.

**Who looks at it:** a technical hiring person (recruiter, team lead). They judge two things:
1. Code quality: structure, tests, commit history.
2. The process of working with an AI agent (Claude Code): specs, plans, CLAUDE.md, meaningful commits, an honest account of where the agent had to be corrected.

**Business problem:** American air duct cleaning companies often do not pick up the phone (crew on a job, evening, weekend) and lose customers. The customer calls the next company on the list.

**Timeline:** 7 days. **Budget:** $0 for development, with a $5-10 reserve for an emergency. Voice runs on LiveKit Inference credits of the Build plan: $2.50 per month, about 50 minutes, a hard cap with no overage charges. So voice is used only for manual checks (23.11: no demo video).

## 2. What the system does

```
Customer calls (button on the demo page; bonus: a real US number)
        ↓
Voice agent answers on behalf of the company (in English)
        ↓
Asks: what is needed, address/ZIP, number of systems and vents, extra services
        ↓
Checks the service area → calculates an approximate price → looks for free slots
        ↓
Agrees on a time, confirms the details, creates a Google Calendar event
        ↓
To the customer: email confirmation + SMS (shown in the demo, not sent)
To the owner: a message by email and Slack
```

## 3. Goals, non-goals, anti-goals

**Goals**
- The agent takes the conversation all the way to a calendar booking with no human involved.
- Slots are real: the agent sees only free time from Google Calendar, double booking is impossible.
- Code calculates the price from the price list; the model only collects data and calls a function.
- A price always sounds like an estimate: "About $520, the technician confirms the exact amount on site."
- Service area check by ZIP code.
- If the customer asks for a live person: the agent takes a message and passes it to the owner.
- A recruiter can try the agent themselves (button in the browser). When the live demo is offline, the README proves the work on its own: screenshots of a real call and its transcript (23.11: replaces the planned 1-2 minute video).
- A one-page website for the fictional company, built from scratch (services, "from" prices, service area, how a cleaning goes, FAQ, contacts) with a "Talk to our AI assistant" button. The site replaces a separate demo page. The main way to book on the site is by voice through the agent (author's decision). The design is agreed with the author on mockups before any code is written.

**If time remains (author's decision)**
- A full multi-page website.
- Booking through a text chat on the site.

**Priority:** the agent is the main thing in the project. If it does not work from call to calendar booking by the end of day 5, the website is reduced to a minimum.
- The repository shows the agentic programming process.

**Non-goals (deliberately not done this week)**
- Rescheduling and cancelling bookings.
- Advice about mold, repairs, air quality. The agent answers: "The technician will assess on site."
- Languages other than English.
- Real SMS sending (see the 10DLC restriction).
- Integrations with industry CRMs (Jobber, Housecall Pro).

**Anti-goals (a failure even if it works technically)**
- A "chatbot that forwards text to a model": no real tools and no data.
- The agent states a price, slot or service that is not in the data.
- Double booking of one time.
- A demo that does not work when the recruiter presses the button, with nothing in the README that shows a real call (23.11: screenshots and a call transcript instead of a video).
- API keys or secrets in the repository.
- Made-up customer reviews on the site.
- Code the author cannot explain in an interview.

## 4. Constraints

- **SMS in the US:** any SMS sent from an app through a 10-digit number requires A2P 10DLC registration with a company tax ID. The Sole Proprietor option is available only to senders from the US and Canada. So the Twilio SMS sending code is written in full but switched off by a flag (`SMS_ENABLED=false`). In the demo the SMS text is shown on the page. The README explains why.
- **Free tiers:** LiveKit Cloud Build (1000 agent minutes per month, no card, one free US number, cold start); Gemini Live through LiveKit Inference ($2.50 credits per month, about 50 minutes). The voice model name is a single value `VOICE_MODEL` in `.env` so it can be replaced.
- **Result of the first-day spike (19.11):** Gemini Live is not available for the AI Studio key: the direct Google plugin returns HTTP 404. Through LiveKit Inference (`google/gemini-3.8-live`, voice Puck, ai-coustics noise cancellation) the agent answers by voice. Decision: voice goes through LiveKit Inference exactly as in the spike; the AI Studio key (free tier) is used only for text conversation tests.
- **Text model for tests (checked 19.11):** `gemini-2.5-flash` is closed to new users; `gemini-3.5-flash-lite` answered; `gemini-3.8-flash` exists but answered 503 "high demand". The model name is in `TEST_LLM_MODEL` (default `gemini-3.5-flash-lite`; `gemini-3.8-flash` as an option once it stops returning 503).
- **Public demo limits sized to 50 minutes per month:** a call lasts up to 5 minutes (300 s); there is no daily call limit. The README and the site say the live demo has a small monthly voice budget. When the credits are exhausted (the agent does not answer), the site says the live demo is paused and links to the GitHub repository (23.11: there is no video).
- **The company is fictional.** The name and brand must not match a real company. The demo page carries the text: "Fictional company, demo only".
- The author is only starting to learn agentic programming, so the code must be simple to read and explain. No unnecessary abstractions.

## 5. Approaches considered

| Approach | Pros | Cons |
|---|---|---|
| A. Vapi + own tool server | Simplest, ready call button, popular among integrators | Only $5-10 of starting credits, then about $0.08-0.13/min; logic lives in their dashboard, less visible in the repository |
| **B. LiveKit Agents + Gemini Live** ✅ | The whole agent is in the repository code; $0 on free tiers; a recognizable framework (it powers ChatGPT voice mode) | More complex; free tier limits are not guaranteed; cold start |
| C. Fully local (Whisper + Ollama + local TTS) | $0 forever | Local models call tools badly, and the whole idea depends on that; a recruiter cannot call it |

**B chosen** (author's decision), because it gives the most visible work in the repository at zero budget.

## 6. Decisions made by the author

- The voice agent leads the customer to a booking: checks slots, agrees a time, books.
- After booking: an SMS to the customer and a message to the owner.
- Slots are stored in Google Calendar.
- SMS: the code exists but is switched off; the demo shows an SMS log.
- Owner messages go through two channels: email and Slack.
- The recruiter tries the agent through a button in the browser (23.11: the planned video is dropped, see below); a real US number is a bonus.
- The agent has access to the price list and calculates the total price for the customer's needs.
- The price is presented as an estimate.
- The fictional company's price list uses real market numbers, in a separate file.
- Boundaries: the ZIP check and passing a message to a live person are part of the project.
- Approach B: LiveKit Agents + Gemini Live (through LiveKit Inference after the first-day spike).
- A 4-hour slot with a buffer for travel.
- We write the company website ourselves and agree the design on mockups. The "Handyman's Van" direction (B) was chosen: dark green #0D4A42, yellow #F5C518, fonts Barlow Condensed + Barlow, on the first screen a mockup of a conversation with the agent that ends in a booking. A line-by-line price calculation example (from direction C) was added to this direction.
- City: Atlanta, Georgia.
- (19.11) Voice through LiveKit Inference, as in the working spike; the model is a single value `VOICE_MODEL`. The budget is about 50 minutes per month, so voice is used only for manual checks (23.11: no demo video).
- (19.11) Conversation tests run on a Gemini text model through the AI Studio key (`GOOGLE_API_KEY`, free tier), not through LiveKit Inference, so they do not spend voice credits.
- (19.11) Double booking protection without an in-process lock (sessions may run in separate processes): see section 7.
- (19.11) No daily session limit; a call lasts up to 300 s.
- (19.11) The agent is deployed to LiveKit Cloud as soon as it works locally. Deploy with project keys, because `lk cloud auth` does not work on Windows.
- (19.11) The README says directly that the live demo has a small monthly voice budget. (23.11: the video part is dropped, see the next point.)
- (23.11) No video. The README is a long-lived portfolio case study, not a 2-minute pitch: it must prove the work on its own, even when the live demo is offline. So the Demo section has screenshots (the site, a call with both panel cards, the calendar event, the Slack message) and a short real call transcript. The site links to the GitHub repository ("see how it works") instead of a video. The README also has a "Results" section (measured facts only) and "What I would do for a real client" (next steps, not built).

Mockups: https://claude.ai/artifact/2KjFptJQ1y9STLvXgXHRxh

## 7. Claude's decisions (the author can change them)

- **Language:** Python (the primary one for LiveKit Agents, easiest to read and explain).
- **Arithmetic only in code:** the function `calculate_quote(...)` returns the total and a breakdown. The model does not recalculate it.
- **Price list** (within the Housecall Pro 2026 market ranges), file `config/pricing.yaml`:
  - Cleaning one system: $449, includes up to 10 vents
  - Each additional vent: $35
  - Second and later systems: $349 each
  - Dryer vent cleaning: $129
  - Antimicrobial treatment: $99 per system
  - Blower cleaning: $179 per system
- **If the customer does not know the number of vents:** the agent asks the house area, and code estimates the number of vents from a simple table (for example, up to 1500 sq ft → 10, up to 2500 → 14, larger → 18). The price is then explicitly called "approximate".
- **Schedule:** one crew; work days Mon-Sat; each slot is 4 hours with a buffer for travel (author's decision); two slots a day, 8:00-12:00 and 13:00-17:00, with a one-hour break between them (Claude's decision, so the working day does not go past 17:00); the time zone of the company's city. Booking is possible from the next day up to 14 days ahead. All of it is in `config/business.yaml`.
- **Company:** Draftwell (no company with this name was found in the industry), phone on the site (404) 555-0142 from the range of fictional numbers.
- **Service area:** ZIP codes of Atlanta, Decatur, Brookhaven, Sandy Springs, Dunwoody and Smyrna, in the config. Time zone America/New_York.
- **Double booking protection (author's decision 19.11):** no in-process lock, because sessions may run in separate processes. Before booking, the code checks the slot is free; after creating the event it re-reads the events of that slot. If there is more than one and ours is not the earliest (by creation time), the code deletes our event, and the agent tells the customer the time is already taken and offers others. There is a test for this.
- **Calendar access:** a Google service account with which the company calendar is shared.
- **SMS and notification log on the demo page:** the agent passes the SMS text for the customer and the message for the owner to the page through the LiveKit data channel. The page shows them in a side panel ("customer's phone" and "owner's phone") right during the call. No separate database is needed.
- **Customer data:** name, phone, email, address with ZIP, number of systems, vents (or area), extra services, preferred time. The agent repeats the key data before booking.
- **Customer email is optional.** The agent asks the customer to spell it letter by letter and repeats it before booking. Without an email the customer gets only the "SMS" in the demo panel.
- **Public demo protection:** a separate demo calendar (not the author's personal calendar); a call is limited to 5 minutes (300 s). There is no daily session limit (author's decision 19.11).
- **The agent introduces itself as a virtual assistant**, not a human.
- **Documentation language in the repository:** English (README, specs, comments). This document is in Ukrainian for approval; the English version goes into the repository on day one.

## 8. How agentic programming is shown

- `CLAUDE.md` with project rules for the agent.
- `docs/specs/` and `docs/plans/`: this design and the implementation plan.
- Small meaningful commits, each closing one step of the plan.
- A README section "How this was built with Claude Code": how the work went, where the agent made mistakes and how they were fixed, what the author decided personally.

## 9. How we check it works

- **Unit tests** (pytest): price calculation, vent estimate from area, ZIP check, finding free slots, double booking protection, including when another session created an event in the same slot slightly earlier (the calendar is faked in tests).
- **Conversation tests:** scenarios "normal booking", "does not know the number of vents", "ZIP outside the area", "wants a live person", "asks about mold", "asks for a discount / a price that does not exist". We check that the agent called the right tools and did not state numbers that are not in the tool results. These tests always run with a Gemini text model through the AI Studio key (free tier), not through LiveKit Inference, so they do not spend voice credits.
- **Manual check:** a real call through the demo page, the booking appears in the calendar, email and Slack arrive. Voice calls are kept to a minimum because the budget is about 50 minutes per month.
- **CI:** GitHub Actions runs the unit tests on every push.

## 10. What is delivered

- A public GitHub repository with the agent code, the demo page, tests, configuration and documentation.
- The company website on free hosting with a "Talk to our AI assistant" button and a side panel for SMS/messages.
- The agent deployed to LiveKit Cloud so a recruiter can call without the author's PC running.
- In the README: screenshots of a real call (the site, the call with both panel cards, the calendar event, the Slack message) and a short call transcript, so the work is shown even when the live demo is offline (23.11: replaces the planned 1-2 minute video).
- Bonus, if time remains: a real US number from LiveKit.

## 11. Where things live

| Part | Where | Why not GitHub |
|---|---|---|
| Code, documentation, tests, CI | GitHub (repository + GitHub Actions) | That is GitHub itself |
| Voice agent (Python, runs continuously) | LiveKit Cloud (free Build) | GitHub does not run servers that wait for calls |
| Company website + access token function | Netlify (free tier; planned as Vercel, which blocked the account's phone verification) | GitHub Pages serves only static files, and the token must be signed with a secret key that cannot go into page code |
| Voice model, text model for tests, calendar, email, Slack | LiveKit Inference, Gemini API (AI Studio key), Google Calendar, an email service, Slack | External services |

Deploys to LiveKit Cloud and Netlify come from the same repository.

## 12. What is left to the developer

- The structure of folders and modules, function names (except `calculate_quote`).
- The exact list of ZIP codes for the listed cities.
- The email service (any with a free tier) and the text of the emails.
- The demo page template (for example, the official LiveKit starter template) and hosting.
- The text of the agent's system prompt within the rules of this document.
- The order of work by day (in the implementation plan).
