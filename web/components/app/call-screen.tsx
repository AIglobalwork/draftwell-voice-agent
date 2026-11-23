'use client';

import { useEffect, useState } from 'react';
import { useAgent, useSessionContext, useSessionMessages } from '@livekit/components-react';
import { DemoPanel } from '@/components/DemoPanel';
import { AgentChatTranscript } from '@/components/agents-ui/agent-chat-transcript';
import { AgentDisconnectButton } from '@/components/agents-ui/agent-disconnect-button';
import { AgentTrackToggle } from '@/components/agents-ui/agent-track-toggle';
import { useInputControls } from '@/hooks/agents-ui/use-agent-control-bar';
import { REPO_URL } from '@/lib/demo';

function formatTime(seconds: number) {
  const minutes = Math.floor(seconds / 60);
  return `${minutes}:${String(seconds % 60).padStart(2, '0')}`;
}

// Seconds since the call connected.
function useCallTimer(running: boolean) {
  const [seconds, setSeconds] = useState(0);
  useEffect(() => {
    if (!running) return;
    const id = setInterval(() => setSeconds((s) => s + 1), 1000);
    return () => clearInterval(id);
  }, [running]);
  return seconds;
}

interface CallScreenProps {
  paused: boolean;
  onClose: () => void;
  onPaused: () => void;
}

// Full-screen call view over the page: status, timer, mic, end call, conversation, demo panel.
export function CallScreen({ paused, onClose, onPaused }: CallScreenProps) {
  const session = useSessionContext();
  const agent = useAgent();
  const { messages } = useSessionMessages(session);
  const { microphoneToggle } = useInputControls({ saveUserChoices: false });
  const seconds = useCallTimer(session.isConnected && !paused);

  // The agent did not join (for example the monthly voice credits are used up).
  useEffect(() => {
    if (agent.state === 'failed') {
      session.end();
      onPaused();
    }
  }, [agent.state, session, onPaused]);

  const status = agent.isConnected ? 'Call in progress' : 'Connecting…';

  return (
    <div
      role="dialog"
      aria-label="Call with the Draftwell AI assistant"
      className="fixed inset-0 z-50 flex flex-col gap-3 bg-[#0D4A42] p-3 text-white md:gap-4 md:p-6"
    >
      {paused ? (
        <div className="m-auto flex max-w-md flex-col items-start gap-5">
          <h1 className="font-condensed text-5xl leading-none font-extrabold">
            The live demo is paused right now.
          </h1>
          <p className="text-lg leading-snug text-[#D9E7E4]">
            <a href={REPO_URL} className="font-semibold text-white underline">
              See how it works
            </a>{' '}
            on GitHub, with screenshots and a transcript of a real call.
          </p>
          <button
            type="button"
            onClick={onClose}
            className="min-h-[54px] rounded-full bg-[#F5C518] px-7 text-lg font-bold text-[#1C2124]"
          >
            Back to the page
          </button>
        </div>
      ) : (
        <>
          <header className="flex items-center gap-3">
            <span className="font-condensed text-2xl font-extrabold italic md:text-3xl">
              Draftwell
            </span>
            <span className="mr-auto text-sm md:text-base">
              <span className="font-bold">{status}</span>{' '}
              <span className="text-[#D9E7E4]">{formatTime(seconds)}</span>
            </span>
            <AgentTrackToggle
              source="microphone"
              size="lg"
              variant="outline"
              pressed={microphoneToggle.enabled}
              disabled={microphoneToggle.pending}
              onPressedChange={microphoneToggle.toggle}
              aria-label={microphoneToggle.enabled ? 'Mute microphone' : 'Unmute microphone'}
              className="rounded-full bg-white text-[#1C2124]"
            />
            <AgentDisconnectButton size="lg" className="rounded-full" onClick={onClose} />
          </header>
          <div className="grid min-h-0 flex-1 grid-rows-[auto_minmax(0,1fr)] gap-3 md:grid-cols-[minmax(0,1fr)_380px] md:grid-rows-1 md:gap-4">
            <div className="order-2 min-h-0 overflow-hidden rounded-2xl bg-white text-[#1C2124] md:order-1">
              <AgentChatTranscript
                agentState={agent.state}
                messages={messages}
                className="h-full **:data-[slot=message-scroller-content]:p-4"
              />
            </div>
            <div className="order-1 min-h-0 md:order-2">
              <DemoPanel />
            </div>
          </div>
        </>
      )}
    </div>
  );
}
