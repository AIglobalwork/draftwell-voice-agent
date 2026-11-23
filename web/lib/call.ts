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
