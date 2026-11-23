'use client';

import { useCallback, useMemo, useState } from 'react';
import { TokenSource } from 'livekit-client';
import { useSession } from '@livekit/components-react';
import { AgentSessionProvider } from '@/components/agents-ui/agent-session-provider';
import { StartAudioButton } from '@/components/agents-ui/start-audio-button';
import { CallScreen } from '@/components/app/call-screen';
import { SitePage } from '@/components/app/site-page';
import { useDebugMode } from '@/hooks/useDebug';

const IN_DEVELOPMENT = process.env.NODE_ENV !== 'production';

function AppSetup() {
  useDebugMode({ enabled: IN_DEVELOPMENT });
  return null;
}

export function App() {
  const tokenSource = useMemo(() => TokenSource.endpoint('/api/token'), []);
  const session = useSession(tokenSource);
  const [callOpen, setCallOpen] = useState(false);
  const [paused, setPaused] = useState(false);

  const startCall = async () => {
    setPaused(false);
    setCallOpen(true);
    try {
      await session.start();
    } catch (error) {
      // The connection failed: treat the live demo as paused.
      console.error(error);
      setPaused(true);
    }
  };

  const onPaused = useCallback(() => setPaused(true), []);
  const onClose = useCallback(() => setCallOpen(false), []);

  return (
    <AgentSessionProvider session={session}>
      <AppSetup />
      <SitePage onStartCall={startCall} />
      {callOpen && <CallScreen paused={paused} onPaused={onPaused} onClose={onClose} />}
      <StartAudioButton label="Start Audio" />
    </AgentSessionProvider>
  );
}
