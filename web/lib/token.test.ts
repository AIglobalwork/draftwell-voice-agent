import { TokenVerifier } from 'livekit-server-sdk';
import { expect, test } from 'vitest';
import { createDemoToken } from './token';

const KEY = 'test-key';
const SECRET = 'test-secret-that-is-long-enough-for-hs256';

test('token is scoped to one fresh demo room and one narrow job', async () => {
  const a = await createDemoToken(KEY, SECRET);
  const b = await createDemoToken(KEY, SECRET);

  expect(a.roomName).toMatch(/^draftwell-demo-/);
  expect(a.roomName).not.toBe(b.roomName);
  expect(a.participantIdentity).not.toBe(b.participantIdentity);

  const claims = await new TokenVerifier(KEY, SECRET).verify(a.participantToken);
  expect(claims.sub).toBe(a.participantIdentity);

  // Only join this room and publish the microphone and data (the pre-connect audio buffer is a data stream). No admin grants.
  expect(claims.video).toEqual({
    room: a.roomName,
    roomJoin: true,
    canSubscribe: true,
    canPublish: true,
    canPublishSources: ['microphone'],
    canPublishData: true,
  });

  // Dispatch only the draftwell agent; room holds the caller and the agent only.
  expect(claims.roomConfig?.agents).toHaveLength(1);
  expect(claims.roomConfig?.agents?.[0]?.agentName).toBe('draftwell');
  expect(claims.roomConfig?.maxParticipants).toBe(2);
  expect(claims.roomConfig?.emptyTimeout).toBe(60);

  // Short lifetime: about 2 minutes.
  const secondsLeft = (claims.exp ?? 0) - Math.floor(Date.now() / 1000);
  expect(secondsLeft).toBeGreaterThan(100);
  expect(secondsLeft).toBeLessThanOrEqual(120);
});
