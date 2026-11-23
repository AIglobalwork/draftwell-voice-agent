import { expect, test } from 'vitest';
import { parsePanelEvent, readPanelEvent } from './panel';

test('parses valid panel events and rejects junk', () => {
  expect(parsePanelEvent('{"type":"sms_to_customer","text":"Hi","delivered":false}')).toEqual({
    type: 'sms_to_customer',
    text: 'Hi',
    delivered: false,
  });
  expect(parsePanelEvent('{"type":"other"}')).toBeNull();
  expect(parsePanelEvent('not json')).toBeNull();
});

test('readPanelEvent returns null when the stream fails, instead of throwing', async () => {
  const broken = { readAll: () => Promise.reject(new Error('stream closed')) };
  expect(await readPanelEvent(broken)).toBeNull();

  const good = {
    readAll: () =>
      Promise.resolve('{"type":"owner_notification","text":"New booking","delivered":true}'),
  };
  expect(await readPanelEvent(good)).toEqual({
    type: 'owner_notification',
    text: 'New booking',
    delivered: true,
  });
});
