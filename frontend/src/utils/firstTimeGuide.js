// The first-time guide is a short tour of the feed shown once to people who
// have just registered. It is remembered per account in this browser.
const keyFor = email => `firstTimeGuide:${String(email || '').trim().toLowerCase()}`;

export const GUIDE_START_EVENT = 'candornews:start-guide';

// Called after a successful registration, so the tour opens after the first login.
export const markGuidePending = email => {
  try { localStorage.setItem(keyFor(email), 'pending'); } catch { /* storage unavailable */ }
};

export const isGuidePending = email => {
  try { return localStorage.getItem(keyFor(email)) === 'pending'; } catch { return false; }
};

export const markGuideDone = email => {
  try { localStorage.setItem(keyFor(email), 'done'); } catch { /* storage unavailable */ }
};

// Replays the tour (for example from the Help page).
export const startGuide = () => window.dispatchEvent(new Event(GUIDE_START_EVENT));
