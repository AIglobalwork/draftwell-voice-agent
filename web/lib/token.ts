import { AccessToken, RoomConfiguration, TrackSource } from 'livekit-server-sdk';

// Explicit dispatch: the agent registered under this name joins every new room.
const AGENT_NAME = 'draftwell';

// Public demo design: anyone who opens the site may ask for a token, with no login.
// That is acceptable only because a token can do one narrow thing: join its own fresh
// random room, publish the microphone, and get the draftwell agent dispatched.
// It cannot create other rooms or admin anything; data goes only to its own room.
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
    // The browser sends the pre-connect audio buffer (the caller's first words while the
    // agent joins) as a data stream, so data publishing must be allowed. Data only reaches
    // the other participants of this room, that is the agent.
    canPublishData: true,
  });
  // The room holds the caller and the agent only, and closes soon after it empties.
  at.roomConfig = new RoomConfiguration({
    agents: [{ agentName: AGENT_NAME }],
    maxParticipants: 2,
    emptyTimeout: 60,
  });

  return { roomName, participantIdentity, participantToken: await at.toJwt() };
}
