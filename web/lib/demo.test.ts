import { expect, test } from 'vitest';
import { REPO_URL } from './demo';

// When the live demo is paused, the site sends visitors to the repository:
// screenshots, a real call transcript and the code.
test('the "see how it works" link points to the GitHub repository', () => {
  expect(REPO_URL).toBe('https://github.com/AIglobalwork/draftwell-voice-agent');
});
