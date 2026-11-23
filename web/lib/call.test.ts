import { expect, test, vi } from 'vitest';
import {
  AGENT_CONNECT_TIMEOUT_MS,
  NEW_CALL,
  callStatus,
  shouldPause,
  startOrEnd,
  trackAgent,
} from './call';

test('a failed start ends the session and reports false', async () => {
  const session = {
    start: vi.fn().mockRejectedValue(new Error('no agent')),
    end: vi.fn().mockResolvedValue(undefined),
  };
  expect(await startOrEnd(session)).toBe(false);
  expect(session.end).toHaveBeenCalledOnce();
});

test('a failed end after a failed start does not throw', async () => {
  const session = {
    start: vi.fn().mockRejectedValue(new Error('no agent')),
    end: vi.fn().mockRejectedValue(new Error('already closed')),
  };
  expect(await startOrEnd(session)).toBe(false);
});

test('a successful start reports true and keeps the session', async () => {
  const session = { start: vi.fn().mockResolvedValue(undefined), end: vi.fn() };
  expect(await startOrEnd(session)).toBe(true);
  expect(session.end).not.toHaveBeenCalled();
});

// b) Cold start: after a quiet period the agent took 25-27 s to join (sessions RM_kzoLVKEGRM6n,
// RM_UpvB4pBS8737), but the components library gives up after 20 s by default.
test('the call waits a minute for the agent to join', () => {
  expect(AGENT_CONNECT_TIMEOUT_MS).toBe(60_000);
});

test('while the agent has not joined, the status says it is waking up', () => {
  expect(callStatus(false)).toBe(
    'Waking up the assistant. The first call after a quiet period can take up to a minute.'
  );
  expect(callStatus(true)).toBe('Call in progress');
});

// c) The agent can join and leave without a word (for example the voice model answers 429).
function progressThrough(states: string[]) {
  return states.reduce(trackAgent, NEW_CALL);
}

test('an agent that joins and leaves without speaking pauses the demo', () => {
  const progress = progressThrough(['connecting', 'initializing', 'listening']);
  expect(shouldPause(progress, 'listening')).toBe(false); // joined: the greeting is on its way
  expect(shouldPause(progress, 'connecting')).toBe(true); // left the room, never spoke
  expect(shouldPause(progress, 'disconnected')).toBe(true);
});

test('an agent that spoke and then left does not pause the demo', () => {
  const progress = progressThrough(['connecting', 'listening', 'speaking', 'listening']);
  expect(shouldPause(progress, 'disconnected')).toBe(false);
});

test('the agent not joining before the timeout pauses the demo', () => {
  expect(shouldPause(NEW_CALL, 'connecting')).toBe(false); // still waking up
  expect(shouldPause(NEW_CALL, 'failed')).toBe(true);
});
