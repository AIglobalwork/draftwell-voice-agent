import { NextResponse } from 'next/server';
import { createDemoToken } from '@/lib/token';

// Public on purpose: see lib/token.ts for why a token from this route is safe to hand out.

// don't cache the results
export const revalidate = 0;

export async function POST() {
  const serverUrl = process.env.LIVEKIT_URL;
  const apiKey = process.env.LIVEKIT_API_KEY;
  const apiSecret = process.env.LIVEKIT_API_SECRET;

  if (!serverUrl || !apiKey || !apiSecret) {
    // Log which variable is missing, but never send details or values to the browser.
    console.error('Token route: LIVEKIT_URL, LIVEKIT_API_KEY or LIVEKIT_API_SECRET is not set');
    return new NextResponse('Server is not configured', { status: 500 });
  }

  try {
    const { roomName, participantIdentity, participantToken } = await createDemoToken(
      apiKey,
      apiSecret
    );
    return NextResponse.json(
      { serverUrl, roomName, participantName: participantIdentity, participantToken },
      { headers: { 'Cache-Control': 'no-store' } }
    );
  } catch (error) {
    console.error('Token route: could not create token', error);
    return new NextResponse('Could not create token', { status: 500 });
  }
}
