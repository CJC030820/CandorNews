import React from 'react';
import { render, screen, fireEvent, within } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import HistoryPage from './HistoryPage';
import BookmarksPage from './BookmarksPage';

const today = new Date().toISOString();
const old = new Date(Date.now() - 40 * 24 * 3600 * 1000).toISOString();
const mockArticles = [
  { id: '1', title: 'Budget passed in Parliament', source: 'New Straits Times', categories: ['Politics'], readAt: today, savedAt: today },
  { id: '2', title: 'Ringgit strengthens', source: 'Free Malaysia Today', categories: ['Business'], readAt: old, savedAt: old },
];

jest.mock('../context/ReadArticlesContext', () => ({
  useReadArticles: () => ({ history: mockArticles, removeFromHistory: jest.fn(), clearHistory: jest.fn() }),
}));
jest.mock('../context/BookmarkContext', () => ({
  useBookmarks: () => ({ bookmarks: mockArticles, removeBookmark: jest.fn() }),
}));

beforeEach(() => { window.scrollTo = jest.fn(); });

const titles = () => screen.queryAllByRole('heading', { level: 3 }).map((h) => h.textContent);

test.each([
  ['History', HistoryPage, 'Time viewed'],
  ['Bookmarks', BookmarksPage, 'Time saved'],
])('%s page filters by keyword, time and category', (_, Page, timeLabel) => {
  render(<MemoryRouter><Page /></MemoryRouter>);
  expect(titles()).toEqual(['Budget passed in Parliament', 'Ringgit strengthens']);
  expect(screen.getByText('Showing 2 of 2')).toBeInTheDocument();

  fireEvent.change(screen.getByLabelText(timeLabel), { target: { value: '7d' } });
  expect(titles()).toEqual(['Budget passed in Parliament']);

  fireEvent.change(screen.getByLabelText(timeLabel), { target: { value: 'all' } });
  fireEvent.change(screen.getByLabelText('Category'), { target: { value: 'Business' } });
  expect(titles()).toEqual(['Ringgit strengthens']);

  fireEvent.change(screen.getByLabelText('Search by keyword'), { target: { value: 'budget' } });
  expect(titles()).toEqual([]);
  expect(screen.getByText(/match these filters/)).toBeInTheDocument();

  fireEvent.click(within(screen.getByRole('search')).getByText('Clear filters'));
  expect(titles()).toHaveLength(2);
  expect(screen.getByText('Showing 2 of 2')).toBeInTheDocument();
});

test('picking a date shows a date input', () => {
  render(<MemoryRouter><HistoryPage /></MemoryRouter>);
  fireEvent.change(screen.getByLabelText('Time viewed'), { target: { value: 'date' } });
  expect(screen.getByLabelText('Time viewed date')).toBeInTheDocument();
});
