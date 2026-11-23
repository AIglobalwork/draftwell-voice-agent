// Starts the call. If connecting fails (no token, agent not dispatched, credits used up),
// the half-open session is ended so the microphone and the room connection are released.
// Returns false when the call could not start.
export async function startOrEnd(session: {
  start(): Promise<void>;
  end(): Promise<void>;
}): Promise<boolean> {
  try {
    await session.start();
    return true;
  } catch (error) {
    console.error('Could not start the call', error);
    try {
      await session.end();
    } catch {
      // Nothing more to release.
    }
    return false;
  }
}

// After a quiet period the agent can take 25-27 s to start (cold start), but the components
// library marks it "failed" after 20 s by default. Wait a minute instead.
export const AGENT_CONNECT_TIMEOUT_MS = 60_000;

export function callStatus(agentConnected: boolean): string {
  return agentConnected
    ? 'Call in progress'
    : 'Waking up the assistant. The first call after a quiet period can take up to a minute.';
}

// What the agent has done so far in this call.
export interface CallProgress {
  joined: boolean;
  spoke: boolean;
}

export const NEW_CALL: CallProgress = { joined: false, spoke: false };

const JOINED_STATES = new Set(['listening', 'thinking', 'speaking']);

export function trackAgent(progress: CallProgress, agentState: string): CallProgress {
  return {
    joined: progress.joined || JOINED_STATES.has(agentState),
    spoke: progress.spoke || agentState === 'speaking',
  };
}

// Show the paused screen when the agent never joined, or joined and left without a word
// (for example the voice model answered 429): not a silent "Call in progress".
export function shouldPause(progress: CallProgress, agentState: string): boolean {
  if (agentState === 'failed') return true;
  return progress.joined && !progress.spoke && !JOINED_STATES.has(agentState);
}
