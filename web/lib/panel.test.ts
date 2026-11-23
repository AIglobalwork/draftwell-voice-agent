import { expect, test } from 'vitest';
import { parsePanelEvent } from './panel';

test('parses valid panel events and rejects junk', () => {
  expect(parsePanelEvent('{"type":"sms_to_customer","text":"Hi","delivered":false}')).toEqual({
    type: 'sms_to_customer',
    text: 'Hi',
    delivered: false,
  });
  expect(parsePanelEvent('{"type":"other"}')).toBeNull();
  expect(parsePanelEvent('not json')).toBeNull();
});
