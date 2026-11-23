import { expect, test, vi } from 'vitest';
import { startOrEnd } from './call';

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
