import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import ProfilePage, { formatTime } from './ProfilePage';

const mockUpdate = jest.fn();
const mockUser = { name: 'Reader', email: 'reader@example.com', preferred_topics: [], email_notifications_enabled: true, email_notification_times: ['07:00'] };

jest.mock('../context/AuthContext', () => ({
  useAuth: () => ({
    user: mockUser,
    logout: jest.fn(), updateProfile: jest.fn(), deleteAccount: jest.fn(), sendEmailTest: jest.fn(),
    selectedTopics: [], getSelectedTopics: () => [],
    getEmailStatus: async () => ({ email_notifications_enabled: true, email_notification_times: ['07:00'], max_notification_times: 3, server_configured: true }),
    updateEmailSettings: (...args) => mockUpdate(...args),
  }),
}));
jest.mock('../context/BookmarkContext', () => ({ useBookmarks: () => ({ bookmarks: [] }) }));
jest.mock('../context/ReadArticlesContext', () => ({ useReadArticles: () => ({ readCount: 0 }) }));

const renderPage = () => render(<MemoryRouter><ProfilePage /></MemoryRouter>);
const timeInputs = () => screen.getAllByLabelText(/^Delivery time \d$/);

beforeEach(() => { mockUpdate.mockReset(); window.scrollTo = jest.fn(); });

test('formats 24-hour times for display', () => {
  expect(formatTime('07:00')).toBe('7:00 AM');
  expect(formatTime('12:30')).toBe('12:30 PM');
  expect(formatTime('00:05')).toBe('12:05 AM');
  expect(formatTime('19:45')).toBe('7:45 PM');
});

test('adds up to three custom times and saves them', async () => {
  mockUpdate.mockResolvedValue({ email_notification_times: ['07:00', '12:00', '21:30'] });
  renderPage();
  await waitFor(() => expect(timeInputs()).toHaveLength(1));
  const add = screen.getByRole('button', { name: /Add time/ });
  fireEvent.click(add);
  fireEvent.click(add);
  expect(timeInputs()).toHaveLength(3);
  expect(screen.getByRole('button', { name: /Add time \(maximum 3\)/ })).toBeDisabled();
  fireEvent.change(timeInputs()[2], { target: { value: '21:30' } });
  fireEvent.click(screen.getByRole('button', { name: 'Save times' }));
  await waitFor(() => expect(mockUpdate).toHaveBeenCalledWith({ emailNotificationTimes: ['07:00', '12:00', '21:30'] }));
  expect(await screen.findByText(/Delivery times saved: 7:00 AM, 12:00 PM, 9:30 PM/)).toBeInTheDocument();
});

test('keeps at least one time and rejects duplicates', async () => {
  renderPage();
  await waitFor(() => expect(timeInputs()).toHaveLength(1));
  expect(screen.getByRole('button', { name: 'Remove delivery time 1' })).toBeDisabled();
  expect(screen.getByRole('button', { name: 'Save times' })).toBeDisabled();
  fireEvent.click(screen.getByRole('button', { name: /Add time/ }));
  fireEvent.change(timeInputs()[1], { target: { value: '07:00' } });
  fireEvent.click(screen.getByRole('button', { name: 'Save times' }));
  expect(await screen.findByText('Each delivery time must be different.')).toBeInTheDocument();
  expect(mockUpdate).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole('button', { name: 'Remove delivery time 2' }));
  expect(timeInputs()).toHaveLength(1);
});
