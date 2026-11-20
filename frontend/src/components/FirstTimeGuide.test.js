import React from 'react';
import { render, screen, fireEvent, act } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import FirstTimeGuide, { GUIDE_STEPS } from './FirstTimeGuide';
import { isGuidePending, markGuidePending, startGuide } from '../utils/firstTimeGuide';

jest.mock('../context/AuthContext', () => ({
  useAuth: () => ({ user: { email: 'New.Reader@example.com', name: 'New Reader' } }),
}));

const EMAIL = 'new.reader@example.com';

const renderAt = path => render(
  <MemoryRouter initialEntries={[path]}>
    <FirstTimeGuide />
  </MemoryRouter>
);

beforeEach(() => localStorage.clear());

test('opens on the feed for a newly registered account', () => {
  markGuidePending(EMAIL);
  renderAt('/feed');
  expect(screen.getByRole('dialog')).toHaveTextContent('Welcome to CandorNews');
  expect(screen.getByText(`Step 1 of ${GUIDE_STEPS.length}`)).toBeInTheDocument();
});

test('does not open for an account that has not just registered', () => {
  renderAt('/feed');
  expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
});

test('waits until the feed is showing', () => {
  markGuidePending(EMAIL);
  renderAt('/article/123');
  expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
});

test('steps forward and back, and finishing marks it done', () => {
  markGuidePending(EMAIL);
  renderAt('/feed');
  fireEvent.click(screen.getByRole('button', { name: /show me around/i }));
  expect(screen.getByRole('dialog')).toHaveTextContent(GUIDE_STEPS[1].title);
  fireEvent.click(screen.getByRole('button', { name: /back/i }));
  expect(screen.getByRole('dialog')).toHaveTextContent(GUIDE_STEPS[0].title);

  for (let i = 0; i < GUIDE_STEPS.length - 1; i += 1) {
    fireEvent.click(screen.getByRole('button', { name: /show me around|next/i }));
  }
  expect(screen.getByRole('dialog')).toHaveTextContent("You're all set!");
  fireEvent.click(screen.getByRole('button', { name: /start reading/i }));
  expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  expect(isGuidePending(EMAIL)).toBe(false);
});

test('skip and Escape close the tour for good', () => {
  markGuidePending(EMAIL);
  const { unmount } = renderAt('/feed');
  fireEvent.click(screen.getByRole('button', { name: /skip tour/i }));
  expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  expect(isGuidePending(EMAIL)).toBe(false);
  unmount();

  markGuidePending(EMAIL);
  renderAt('/feed');
  fireEvent.keyDown(document, { key: 'Escape' });
  expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
});

test('can be replayed from the Help page', () => {
  renderAt('/help');
  expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  act(() => startGuide());
  expect(screen.getByRole('dialog')).toHaveTextContent('Welcome to CandorNews');
});
