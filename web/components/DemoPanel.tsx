'use client';

import { useEffect, useState } from 'react';
import { useSessionContext } from '@livekit/components-react';
import { PANEL_TOPIC, type PanelEvent, parsePanelEvent } from '@/lib/panel';

interface PhoneCardProps {
  title: string;
  label?: string;
  events: PanelEvent[];
  showDelivered?: boolean;
}

function PhoneCard({ title, label, events, showDelivered }: PhoneCardProps) {
  return (
    <section className="flex min-h-0 flex-col gap-2 rounded-2xl bg-white p-3 text-[#1C2124] md:gap-3 md:p-4">
      <h2 className="font-condensed text-xl leading-none font-extrabold md:text-2xl">{title}</h2>
      {label && <p className="text-xs font-semibold text-[#4D5559]">{label}</p>}
      <div className="flex min-h-0 flex-col gap-2 overflow-y-auto">
        {events.length === 0 && <p className="text-sm text-[#4D5559]">Nothing yet.</p>}
        {events.map((event, i) => (
          <div key={i} className="rounded-xl bg-[#EBEDEC] px-3 py-2 text-sm leading-snug">
            <p className="whitespace-pre-wrap">{event.text}</p>
            {showDelivered && (
              <p className="mt-1 text-xs font-bold">
                {event.delivered ? 'Delivered' : 'Not delivered'}
              </p>
            )}
          </div>
        ))}
      </div>
    </section>
  );
}

// The two phone cards. The agent sends events on the text topic "draftwell.panel".
export function DemoPanel() {
  const { room } = useSessionContext();
  const [events, setEvents] = useState<PanelEvent[]>([]);

  useEffect(() => {
    room.registerTextStreamHandler(PANEL_TOPIC, async (reader) => {
      const event = parsePanelEvent(await reader.readAll());
      if (event) setEvents((previous) => [...previous, event]);
    });
    return () => room.unregisterTextStreamHandler(PANEL_TOPIC);
  }, [room]);

  return (
    <div className="grid min-h-0 grid-cols-2 gap-3 md:grid-cols-1 md:grid-rows-2">
      <PhoneCard
        title="Customer's phone"
        label="Demo: not sent, see README"
        events={events.filter((e) => e.type === 'sms_to_customer')}
      />
      <PhoneCard
        title="Owner's phone"
        events={events.filter((e) => e.type === 'owner_notification')}
        showDelivered
      />
    </div>
  );
}
