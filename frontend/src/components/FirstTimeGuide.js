import React, { useCallback, useEffect, useLayoutEffect, useRef, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { GUIDE_START_EVENT, isGuidePending, markGuideDone } from '../utils/firstTimeGuide';
import './FirstTimeGuide.css';

// Each step points at an element marked with data-guide="<target>".
// A step without a target (or whose target is not on screen) is shown centred.
export const GUIDE_STEPS = [
  {
    title: 'Welcome to CandorNews',
    body: 'This quick tour shows you around. It takes about a minute, and you can skip it at any time.',
  },
  {
    target: 'categories',
    title: 'Pick what to read',
    body: '"News For You" orders stories around what you read and bookmark. Choose a category to see only that topic.',
  },
  {
    target: 'platforms',
    title: 'Choose trusted platforms',
    body: 'Press "Manage" to follow or unfollow news publishers. Your feed only shows the platforms you follow.',
  },
  {
    target: 'toolbar',
    title: 'Get the latest news',
    body: 'News is collected every 15 minutes from 6am to midnight. Press "Refresh News" to fetch it now at any time, or switch the order to "Newest first".',
  },
  {
    target: 'articles',
    // Just the first article card, not the whole grid.
    selector: '[data-guide="articles"] > :first-child',
    title: 'Read with a trust score',
    body: 'Every article has a trust score based on the source, coverage by other publishers and how neutral its tone is. Open a story to see the full analysis.',
  },
  {
    target: 'search',
    title: 'Search everything',
    body: 'Search all saved articles by keyword. Suggestions appear as you type.',
  },
  {
    target: 'library',
    title: 'Bookmarks and history',
    body: 'Bookmark stories to read later. History keeps what you have opened. Both are saved to your account on every device.',
  },
  {
    target: 'profile',
    title: 'Make it yours',
    body: 'In your Profile you can choose your interests, change your name and set up email news digests.',
  },
  {
    target: 'help',
    title: "You're all set!",
    body: 'Find answers in Help, where you can also take this tour again.',
  },
];

const PAD = 8;     // space between the highlight and its element
const GAP = 14;    // space between the highlight and the card
const MARGIN = 12; // keep the card this far from the window edges

// Visible elements for a step; several (like Bookmarks and History) are highlighted together.
const findTargets = step => {
  if (!step?.target) return [];
  return Array.from(document.querySelectorAll(step.selector || `[data-guide="${step.target}"]`)).filter(el => {
    const r = el.getBoundingClientRect();
    return r.width > 0 && r.height > 0;
  });
};

const boundsOf = elements => {
  const rects = elements.map(el => el.getBoundingClientRect());
  const top = Math.min(...rects.map(r => r.top));
  const left = Math.min(...rects.map(r => r.left));
  const bottom = Math.max(...rects.map(r => r.bottom));
  const right = Math.max(...rects.map(r => r.right));
  return { top, left, width: right - left, height: bottom - top };
};

const FirstTimeGuide = () => {
  const { user } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);
  const [step, setStep] = useState(0);
  const [rect, setRect] = useState(null);
  const [cardPos, setCardPos] = useState(null);
  const cardRef = useRef(null);
  const email = user?.email;
  const onFeed = location.pathname === '/feed';

  // Open once for a newly registered account, when the feed is showing.
  useEffect(() => {
    if (email && onFeed && isGuidePending(email)) { setStep(0); setOpen(true); }
  }, [email, onFeed]);

  // Replay requested from elsewhere (the Help page).
  useEffect(() => {
    const start = () => { setStep(0); setOpen(true); navigate('/feed'); };
    window.addEventListener(GUIDE_START_EVENT, start);
    return () => window.removeEventListener(GUIDE_START_EVENT, start);
  }, [navigate]);

  const close = useCallback(() => {
    setOpen(false);
    if (email) markGuideDone(email);
  }, [email]);

  const current = GUIDE_STEPS[step];
  const last = step === GUIDE_STEPS.length - 1;
  const next = useCallback(() => (last ? close() : setStep(s => s + 1)), [last, close]);
  const back = useCallback(() => setStep(s => Math.max(0, s - 1)), []);

  // Bring the step's element into view, then measure it.
  const measure = useCallback(() => {
    const els = open && onFeed ? findTargets(current) : [];
    if (!els.length) { setRect(null); return; }
    const r = boundsOf(els);
    // Tall elements (the article grid) are highlighted only where they are on screen.
    const top = Math.max(r.top, 0);
    const bottom = Math.min(r.top + r.height, window.innerHeight);
    if (bottom - top < 24) { setRect(null); return; }
    r.top = top; r.height = bottom - top;
    setRect({ top: r.top - PAD, left: r.left - PAD, width: r.width + PAD * 2, height: r.height + PAD * 2 });
  }, [open, onFeed, current]);

  useEffect(() => {
    if (!open) return undefined;
    const [el] = onFeed ? findTargets(current) : [];
    if (el && el.scrollIntoView) el.scrollIntoView({ block: 'center', behavior: 'smooth' });
    measure();
    // Smooth scrolling and late-loading articles move things; measure again.
    const timers = [150, 400, 800].map(ms => setTimeout(measure, ms));
    window.addEventListener('resize', measure);
    window.addEventListener('scroll', measure, true);
    return () => {
      timers.forEach(clearTimeout);
      window.removeEventListener('resize', measure);
      window.removeEventListener('scroll', measure, true);
    };
  }, [open, onFeed, current, measure]);

  // Place the card below the highlight, or above it when there is no room.
  useLayoutEffect(() => {
    const card = cardRef.current;
    if (!open || !card) return;
    if (!rect) { setCardPos(null); return; }
    const vw = window.innerWidth;
    const vh = window.innerHeight;
    const { offsetWidth: w, offsetHeight: h } = card;
    const clamp = (v, min, max) => Math.min(Math.max(min, v), max);
    const centredLeft = clamp(rect.left + rect.width / 2 - w / 2, MARGIN, vw - w - MARGIN);
    const sideTop = clamp(rect.top + rect.height / 2 - h / 2, MARGIN, vh - h - MARGIN);
    const bottom = rect.top + rect.height;
    const right = rect.left + rect.width;
    // Try below, above, right, then left of the highlight; otherwise pin to the bottom.
    if (bottom + GAP + h <= vh - MARGIN) setCardPos({ top: bottom + GAP, left: centredLeft });
    else if (rect.top - GAP - h >= MARGIN) setCardPos({ top: rect.top - GAP - h, left: centredLeft });
    else if (right + GAP + w <= vw - MARGIN) setCardPos({ top: sideTop, left: right + GAP });
    else if (rect.left - GAP - w >= MARGIN) setCardPos({ top: sideTop, left: rect.left - GAP - w });
    else setCardPos({ top: vh - h - MARGIN, left: centredLeft });
  }, [open, rect, step]);

  useEffect(() => { if (open) cardRef.current?.focus(); }, [open, step]);

  useEffect(() => {
    if (!open) return undefined;
    const onKey = e => {
      if (e.key === 'Escape') close();
      else if (e.key === 'ArrowRight') next();
      else if (e.key === 'ArrowLeft') back();
    };
    document.addEventListener('keydown', onKey);
    return () => document.removeEventListener('keydown', onKey);
  }, [open, close, next, back]);

  if (!open || !onFeed || !current) return null;

  const centred = !rect || !cardPos;
  return (
    <div className="guide-root">
      {/* Blocks clicks on the page while the tour is open. */}
      <div className={`guide-backdrop ${rect ? '' : 'guide-backdrop-dim'}`} />
      {rect && <div className="guide-spotlight" style={rect} aria-hidden="true" />}
      <div
        ref={cardRef}
        className={`guide-card ${centred ? 'guide-card-centred' : ''}`}
        style={centred ? undefined : cardPos}
        role="dialog"
        aria-modal="true"
        aria-labelledby="guide-title"
        aria-describedby="guide-body"
        tabIndex={-1}
      >
        <p className="guide-progress">Step {step + 1} of {GUIDE_STEPS.length}</p>
        <h2 id="guide-title">{current.title}</h2>
        <p id="guide-body">{current.body}</p>
        <div className="guide-dots" aria-hidden="true">
          {GUIDE_STEPS.map((_, i) => <span key={i} className={i === step ? 'active' : ''} />)}
        </div>
        <div className="guide-actions">
          {!last && <button type="button" className="guide-skip" onClick={close}>Skip tour</button>}
          <span className="guide-spacer" />
          {step > 0 && <button type="button" className="guide-back" onClick={back}>Back</button>}
          <button type="button" className="guide-next" onClick={next}>
            {step === 0 ? 'Show me around' : last ? 'Start reading' : 'Next'}
          </button>
        </div>
      </div>
    </div>
  );
};

export default FirstTimeGuide;
