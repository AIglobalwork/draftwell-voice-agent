import { AccessToken, RoomConfiguration, TrackSource } from 'livekit-server-sdk';

// Explicit dispatch: the agent registered under this name joins every new room.
const AGENT_NAME = 'draftwell';

// Public demo design: anyone who opens the site may ask for a token, with no login.
// That is acceptable only because a token can do one narrow thing: join its own fresh
// random room, publish the microphone, and get the draftwell agent dispatched.
// It cannot create other rooms, admin anything, or publish data.
// The agent ends every call after 300 s, which caps the voice spend.
export async function createDemoToken(apiKey: string, apiSecret: string) {
  // Nothing from the request is used: the server picks every value.
  const roomName = `draftwell-demo-${crypto.randomUUID()}`;
  const participantIdentity = `caller-${crypto.randomUUID()}`;

  // The token only has to last until the browser joins the room.
  const at = new AccessToken(apiKey, apiSecret, {
    identity: participantIdentity,
    name: 'user',
    ttl: '2m',
  });
  at.addGrant({
    room: roomName,
    roomJoin: true,
    canSubscribe: true,
    canPublish: true,
    canPublishSources: [TrackSource.MICROPHONE],
    // The panel and the transcript are sent by the agent; the caller sends no data.
    canPublishData: false,
  });
  // The room holds the caller and the agent only, and closes soon after it empties.
  at.roomConfig = new RoomConfiguration({
    agents: [{ agentName: AGENT_NAME }],
    maxParticipants: 2,
    emptyTimeout: 60,
  });

  return { roomName, participantIdentity, participantToken: await at.toJwt() };
}
