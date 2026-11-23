// Panel events sent by the agent on the text topic "draftwell.panel".
export const PANEL_TOPIC = 'draftwell.panel';

export type PanelEvent = {
  type: 'sms_to_customer' | 'owner_notification';
  text: string;
  delivered: boolean;
};

// Returns null for anything that is not a valid panel event.
export function parsePanelEvent(raw: string): PanelEvent | null {
  let data: unknown;
  try {
    data = JSON.parse(raw);
  } catch {
    return null;
  }
  if (typeof data !== 'object' || data === null) return null;

  const { type, text, delivered } = data as Record<string, unknown>;
  if (type !== 'sms_to_customer' && type !== 'owner_notification') return null;
  if (typeof text !== 'string' || typeof delivered !== 'boolean') return null;
  return { type, text, delivered };
}
