# Draftwell Voice Agent

[![CI](https://github.com/AIglobalwork/draftwell-voice-agent/actions/workflows/ci.yml/badge.svg)](https://github.com/AIglobalwork/draftwell-voice-agent/actions/workflows/ci.yml)

Small air duct cleaning companies in the US miss a lot of calls. The crew is on a job, it is evening, or it is the weekend. The customer does not leave a voicemail; they call the next company on the list. Draftwell is a voice AI agent that answers those calls 24/7. It checks the address, gives a price estimate, finds a free time, and books the job into the company calendar. The owner gets an email and a Slack message.

Draftwell is a fictional Atlanta company. This is a portfolio project. The agent, the website and the tests are all in this repository.

**My role:** I chose the problem, the niche and the stack, agreed the design spec and the plan with Claude, ran Claude Code task by task with a separate Claude chat reviewing each step, and made every live call to check the real calendar, emails and Slack. Claude Code wrote the code.

**Stack:** Python 3.12, LiveKit Agents, Gemini 3.8 Live (speech-to-speech) through LiveKit Inference, Google Calendar API, Gmail SMTP, Slack webhook, Next.js 15 site on Netlify, pytest, Vitest, GitHub Actions.

## Demo

![The Draftwell website with the "Talk to our AI assistant" button](docs/images/site.png)

![A call in progress: the conversation and the demo panel with both cards, "Customer's phone" and "Owner's phone"](docs/images/call.png)

![The booked appointment as an event in the demo Google Calendar](docs/images/calendar.png)

![The owner's notification about the new booking in Slack](docs/images/slack.png)

**A real call:** [`docs/call-transcript.md`](docs/call-transcript.md) has a short transcript of a booking call.

**Live site:** https://draftwell-demo.netlify.app. Press "Talk to our AI assistant" and allow the microphone. The live demo runs on free tiers and a hosted voice model, so it may be paused or offline. When the monthly voice credits are used up, the agent does not answer and the site says the live demo is paused.

## What a call does

- **Service area check.** The agent asks for the ZIP code and checks it against the list in [`agent/config/business.yaml`](agent/config/business.yaml).
- **Price estimate from code.** Systems, vents and add-ons go to `calculate_quote`, which uses the price list in [`agent/config/pricing.yaml`](agent/config/pricing.yaml). The model only repeats the result and always says the technician confirms the final price on site.
- **Free times from the calendar.** The agent offers only 4-hour windows that are free in Google Calendar, from tomorrow up to 14 days ahead.
- **Read-back.** Before booking, the agent reads back the name, phone, address, time, estimate and email (spelled letter by letter) and waits for "yes".
- **Booking.** The appointment becomes an event in a dedicated demo Google Calendar.
- **Notifications.** The owner gets an email and a Slack message. The customer gets a confirmation email if they gave one. The SMS the customer would get is shown in a panel on the site (see [Why SMS is simulated](#why-sms-is-simulated)).

If the caller wants a person, the agent takes a message for the owner. It does not give mold or repair advice, and it does not reschedule or cancel.

## Results

- **Voice cost:** about $0.02 per minute of call (LiveKit billing, November 2026).
- **Call cap:** every call ends at 5 minutes. The agent warns 30 seconds before the end, then says goodbye with the caller's microphone muted, so the goodbye cannot be cut off. This was checked in a call with the limit set to 60 seconds.
- **Offline tests:** 84 tests with no network and no keys. They cover the price calculation, the service area ZIPs, free slots and the schedule, double booking (losing and winning the race), notifications (a failed one never cancels a booking), the tools and the call timer.
- **Conversation tests:** 15 scenarios run the real instructions and tools on a Gemini text model. They check the tool calls, and an LLM judge checks most replies. They cover:
  - the price comes from the tool;
  - unknown vents lead to a question about square footage;
  - out-of-area ZIPs;
  - a caller who wants a person;
  - a mold question;
  - a discount request;
  - a slot taken during booking;
  - a message that could not be delivered;
  - "this Thursday" resolved from today's date;
  - the email offer, and an email spelled back and not asked for again;
  - no guessed titles;
  - an ambiguous slot choice;
  - "the confirmation is on its way".

  The last full run (November 2026) passed 15 of 15.
- **Web tests:** 7 Vitest tests for the token's scope, panel events, starting a call and the repository link.
- **CI:** GitHub Actions runs the offline agent tests, the web tests and the web build on every push and pull request.

## Architecture

```mermaid
flowchart LR
    browser["Caller's browser<br/>Draftwell site on Netlify"]
    token["Token route api/token<br/>Netlify function"]
    room["LiveKit Cloud room"]
    agent["Draftwell agent<br/>Python, on LiveKit Cloud"]
    model["Gemini Live<br/>via LiveKit Inference"]
    tools["Tools in flows.py<br/>prices, ZIPs, slots in code"]
    calendar["Google Calendar<br/>demo calendar"]
    gmail["Gmail SMTP<br/>owner + customer email"]
    slack["Slack #bookings"]

    browser -->|"1. asks for a token"| token
    token -->|"token: one random room,<br/>dispatch agent 'draftwell'"| browser
    browser <-->|"2. voice (WebRTC)"| room
    room <--> agent
    agent <-->|audio| model
    agent --> tools
    tools --> calendar
    tools --> gmail
    tools --> slack
    agent -.->|"panel events (text stream)"| room
```

| Folder | What is there |
|---|---|
| [`agent/`](agent) | The voice agent. `main.py` starts the session, `agent.py` has the instructions and thin tools, `flows.py` has the tool logic, the other modules hold prices, scheduling, calendar and notifications. |
| [`web/`](web) | The company website (Next.js, built from LiveKit's `agent-starter-react` template), the token route and the demo panel. |
| [`docs/`](docs) | The design spec (English; the Ukrainian original is in `docs/superpowers/specs/`), the implementation plan, the call transcript and the screenshots. |
| [`CLAUDE.md`](CLAUDE.md) | Project rules for the coding agent. |

## Key design decisions

- **Prices and dates are computed in code, never by the model.** `calculate_quote` returns the total and a breakdown. `book_appointment` recomputes the price from its own arguments and never accepts a total from the model. The model gets today's date in Atlanta time in its instructions, and free slots come from the calendar and the schedule in the config. `book` also refuses a ZIP outside the area, so that rule does not depend on the prompt.
- **Double booking is checked after the event is created.** Calls can run in separate processes, so an in-memory lock would protect nothing. `book_slot` checks the slot is free, creates the event, then re-reads the slot. If there are two events and ours is not the earliest (by creation time, then event id), it deletes ours and the agent offers other times. Two tests cover losing and winning that race.
- **A realtime speech-to-speech model.** Gemini Live hears and speaks in one model, so the conversation feels natural and the caller can interrupt. The trade-offs:
  - there is no separate text-to-speech, so fixed lines like the goodbye are generated by the model from an instruction;
  - the model detects the caller's speech on its server, so a reply cannot be marked "do not interrupt";
  - speech recognition can mishear names and emails, so the read-back before booking is the safety net;
  - the conversation tests run on a Gemini text model, so some mistakes only show up in voice calls.
- **The token route is public on purpose, but narrow.** There is no login, so anyone with the URL can start a call. Each token joins only its own new random room, dispatches only the `draftwell` agent, expires in 2 minutes if unused, and can publish only the microphone and data. A room holds at most 2 participants (caller and agent). The worst case is that someone uses up the month's voice credits. The LiveKit free plan has a hard cap and no card, so that costs $0; the site then shows the paused screen.
- **Call time limit with a warning and a goodbye that cannot be cut.** Calls end at 5 minutes. 30 seconds before the end the agent says time is almost up. At the limit the caller's microphone is muted (so nothing can interrupt the goodbye), the agent says goodbye, and the room is deleted.
- **Notifications run in the background.** The agent hears "Booked" as soon as the calendar event exists, so there is no silence while emails and Slack are sent. If the caller hangs up, the agent still waits up to 20 seconds for them to finish. A failed notification never cancels a booking.

## How this was built with Claude Code

I built this with Claude Code as my coding agent. The process:

1. **Brainstorm and design spec.** The idea, the stack and the website design were agreed before any code. See [`docs/specs/`](docs/specs).
2. **Implementation plan.** 11 tasks plus a throwaway voice spike, each with exact files, tests and expected results. See [`docs/plans/`](docs/plans).
3. **Subagent-driven development.** For each task one subagent wrote the code test-first, and a separate reviewer subagent checked it against the plan and for quality. Findings went through a fix loop and a progress log. Rules for the agent are in [`CLAUDE.md`](CLAUDE.md).
4. **A separate planning chat with Claude.** It reviewed the plan and every task report, wrote the prompts I gave to Claude Code, and checked commits and deploys. Claude Code did the implementation.
5. **Manual checks by me.** I made all voice calls and checked the real calendar, emails and Slack.

What happened along the way (who did what is stated in each case):

- **A lock that would not lock.** The first plan prevented double booking with an in-memory lock. A plan review in my planning chat with Claude caught that LiveKit can run each call in its own process: the test with a fake calendar would pass and production would have no protection. It became the create-then-re-read check above.
- **An unverified mail server.** A review found that the SMTP connection did not verify the server certificate, so the Gmail password could be intercepted. It was fixed in a separate commit before the first real email went out.
- **"Your message was passed on" when it was not.** A reviewer found that the message tool always told the caller the message reached the owner, even when email and Slack both failed. Claude Code called it minor and proposed to defer it. I decided to fix it at once: a caller who asked for a person would wait for a call that never comes. Now the agent apologizes and reads out the company phone number.
- **A "flaky" test that was a real bug.** A conversation test failed now and then. Part of it was Gemini overload, but the model also quoted a price without asking for the square footage. Claude Code did not weaken the test. It added a rule to the instructions, as the plan required: fix the instructions, not the test.
- **Silence after "Yes".** In my first voice call the agent went quiet for 6-7 seconds after I confirmed, so I hung up, although the booking was made. The booking tool sent two emails and a Slack message before it answered. Claude Code moved the notifications to a background task and added timing logs for each step.
- **A Windows path in the Dockerfile.** `lk agent dockerfile` on Windows wrote the start path with backslashes. In the JSON form of `CMD`, `\d` is not valid, so the container would not start. Claude Code caught this before the first deploy.
- **The caller's first words.** The implementer of the public token route also turned off data publishing. The task reviewer noticed that LiveKit sends the audio recorded while the agent joins as a data stream, so the caller's first words would be lost. It was fixed before the site went live.
- **A goodbye that never played.** On the live site the goodbye at the time limit did not play; the call just ended. Claude Code checked the cloud logs: no timer error, so the goodbye had ended early. The caller's speech had interrupted it, and Gemini Live ignores the "do not interrupt" flag. The fix mutes the caller before the goodbye. A review of that fix in my planning chat with Claude caught that the new 30-second warning was outside the `try/finally`, so an error there would leave the call with no time limit. That was fixed with its own test.

Other decisions that were mine: the niche and the stack (LiveKit over Vapi or a fully local setup, so all the work is visible in the repository), prices only in code, SMS off with the reason in the README, no video (screenshots and a real call transcript are the proof, so the README stands on its own when the live demo is offline), the website design, and keeping the `Co-Authored-By: Claude` line in commits.

## Run locally

You need Python 3.12 with [uv](https://docs.astral.sh/uv/), Node.js 22 or later, a LiveKit Cloud project (the free Build plan is enough), a Google service account with access to one calendar, a Gmail app password and a Slack incoming webhook.

1. Copy `.env.example` to `.env` in the repository root and fill it in. `GOOGLE_SERVICE_ACCOUNT_JSON` is the whole key file on one line, in single quotes. `.env` is git-ignored; never commit it.
2. Start the agent:

   ```bash
   cd agent
   uv sync
   uv run src/draftwell/main.py console   # talk to the agent in the terminal
   uv run src/draftwell/main.py dev       # or: wait for calls from the website
   ```

   Voice calls use LiveKit Inference credits.
3. Start the website in a second terminal:

   ```bash
   cd web
   cp .env.example .env.local   # LIVEKIT_URL, LIVEKIT_API_KEY, LIVEKIT_API_SECRET
   npm install
   npm run dev                  # http://localhost:3000
   ```

   The site dispatches the agent named `draftwell`. If the same agent is also deployed in your LiveKit project, the cloud agent may take the call instead of your local one.

## Tests

```bash
cd agent
uv run pytest -m "not llm"   # offline: prices, ZIPs, slots, double booking, notifications, tools, call timer
uv run pytest -m llm         # conversation tests on a Gemini text model (needs GOOGLE_API_KEY)

cd ../web
npm test                     # token scope, panel events, call start, repository link
```

- **Offline tests** need no network and no keys. They use a fake calendar and recording senders.
- **Conversation tests** run the real instructions and tools on a Gemini text model through a free AI Studio key, so they spend no voice credits. They check that the agent calls the right tools and says the right things (an LLM judge checks most replies). The free tier allows 15 requests a minute, so there is a 15 s pause after each test (`LLM_TEST_PAUSE_SECONDS`). A full run takes about 6 minutes. Gemini sometimes answers 503 or 429; a single test can then fail for reasons outside the code.
- **CI** ([`.github/workflows/ci.yml`](.github/workflows/ci.yml)) runs the offline agent tests and the web tests and build on every push and pull request. The conversation tests are not in CI, because there is no API key on GitHub.

## Deploy

**Agent on LiveKit Cloud.** In `agent/`: `lk agent create` once (it writes `livekit.toml`), then `lk agent deploy` for each new version. LiveKit builds the image from the [`Dockerfile`](agent/Dockerfile), so Docker is not needed locally. Secrets go to LiveKit's secret store with `lk agent update-secrets`, separate from the code. Do not pass `LIVEKIT_*` (the cloud injects them) or the test-only `GOOGLE_API_KEY` and `TEST_LLM_MODEL`. At startup the agent logs whether the service account JSON arrived intact (only its shape, never its values). Check with `lk agent status` and `lk agent logs`.

**Website on Netlify.** Import the repository with base directory `web`. Build settings and the Next.js adapter are in [`web/netlify.toml`](web/netlify.toml). Set `LIVEKIT_URL`, `LIVEKIT_API_KEY` and `LIVEKIT_API_SECRET` in Netlify (a separate LiveKit API key for the site is best). Every push to `main` deploys the site.

## Why SMS is simulated

In the US, any SMS an app sends from a 10-digit number needs A2P 10DLC registration with a company tax ID. The sole proprietor option is only for senders in the US and Canada. So the Twilio sending code is written but switched off (`SMS_ENABLED=false`), and the site shows the SMS the customer would get in the "Customer's phone" panel.

## Limits of the demo

- $2.50 of free LiveKit Inference credits a month for all visitors together (hard cap). When they run out, the live demo is paused until next month.
- The live demo depends on the hosted voice model. If the model is overloaded or down, a call cannot start.
- A call lasts at most 5 minutes.
- Bookings go to a dedicated demo calendar. One crew, Monday to Saturday, 8 AM-12 PM and 1 PM-5 PM Atlanta time, from tomorrow up to 14 days ahead, closed on listed holidays.
- Service area: Atlanta, Decatur, Brookhaven, Sandy Springs, Dunwoody and Smyrna.
- English only. No rescheduling or cancelling: the agent offers to take a message for the owner instead.
- Every price is an estimate; the technician confirms the final price on site.
- The token route has no login and no rate limit, by design (see above). The free plan also has a cold start, so the first call after a quiet period can take longer to connect.

## Known issues

- **npm advisories that need major upgrades.** `npm audit` in `web/` still reports PostCSS bundled inside Next.js 15 (used only at build time, on our own CSS; fixed only in Next.js 16) and KaTeX under `streamdown`, which renders the call transcript (fixed only in `streamdown` 2). Both need a major upgrade and are not done yet.
- **Voice-only mistakes.** The voice model sometimes mishears names or emails, or once paused for 6-7 seconds after an address. The read-back before booking catches wrong data. Some instruction rules were added after live calls; the text model used in tests already followed them, so those tests guard the rules but did not reproduce the original mistake.
- **Conversation tests depend on the Gemini free tier** and can fail on 503 or 429 errors.

## What I would do for a real client

These are next steps. None of them is built in this demo.

- **A real phone number.** Callers would dial a number (SIP through LiveKit telephony) instead of using the browser.
- **Per-client config.** Prices, ZIP codes and the schedule are already in YAML files in [`agent/config/`](agent/config). Each client would get its own config, calendar and notification channels.
- **Abuse protection and rate limiting.** The token route is open by design in the demo. A real client needs rate limits and bot protection on it.
- **CRM integration.** Bookings and messages would go into the client's CRM, not only to the calendar, email and Slack.
- **Real SMS.** The Twilio code is written. It would be switched on after A2P 10DLC registration under the client's company.
- **Monitoring and alerts.** Alerts on failed bookings, failed notifications and agent errors, plus call metrics.
- **A fallback voice model.** If the voice model is down or overloaded, the agent would switch to another one. The model name is already a single setting (`VOICE_MODEL`).

---

Draftwell is a fictional company. Its name, phone number and prices are made up for this demo.
