# Draftwell website

The website of Draftwell, a fictional Atlanta duct cleaning company. The "Talk to our AI assistant" button starts a voice call with the agent named `draftwell` from [`agent/`](../agent).

It is built from LiveKit's [agent-starter-react](https://github.com/livekit-examples/agent-starter-react) template (Next.js). The template's MIT license is in [`LICENSE`](LICENSE).

## What changed from the template

- **The page:** [`components/app/site-page.tsx`](components/app/site-page.tsx) is the company site: hero, prices, how a visit works, service area, hours and how to reach a person.
- **The call screen and the paused screen:** [`components/app/call-screen.tsx`](components/app/call-screen.tsx) shows the call status, a timer, the microphone toggle, the conversation and the demo panel. If the agent does not join (for example, the monthly voice credits are used up), it shows the paused screen with a link to the repository.
- **The demo panel:** [`components/DemoPanel.tsx`](components/DemoPanel.tsx) shows two cards, "Customer's phone" and "Owner's phone". The agent sends their events on the text stream topic `draftwell.panel`; [`lib/panel.ts`](lib/panel.ts) parses them.
- **The token route:** [`app/api/token/route.ts`](app/api/token/route.ts) uses [`lib/token.ts`](lib/token.ts). The route is public, so each token is narrow:
  - it joins only its own new random room;
  - it dispatches only the `draftwell` agent;
  - it is valid for 2 minutes;
  - it can publish only the microphone and data;
  - the room holds at most 2 participants (the caller and the agent).
- **Voice only:** no camera video and no screen sharing.

## Run locally

You need Node.js 22 or later and a LiveKit Cloud project. The agent must be running too (see the [root README](../README.md#run-locally)).

```bash
cp .env.example .env.local   # LIVEKIT_URL, LIVEKIT_API_KEY, LIVEKIT_API_SECRET
npm install
npm run dev                  # http://localhost:3000
```

`.env.local` is git-ignored; never commit it.

## Test and build

```bash
npm test        # Vitest: token scope, panel events, call start, repository link
npm run build
```

## Deploy

The site runs on Netlify. See [Deploy](../README.md#deploy) in the root README.
