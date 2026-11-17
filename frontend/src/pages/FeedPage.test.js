import React from 'react';
import { render, screen, fireEvent, waitFor, within } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import FeedPage from './FeedPage';

let mockTopics = ['Politics'];
const mockUpdatePreferences = jest.fn();
const articles = [
  { id: '1', title: 'Parliament passes budget', source: 'New Straits Times', date: '2026-11-18T01:00:00Z', categories: ['Politics'] },
  { id: '2', title: 'Harimau Malaya wins final', source: 'New Straits Times', date: '2026-11-18T02:00:00Z', categories: ['Sports'] },
  { id: '3', title: 'Ringgit strengthens', source: 'Free Malaysia Today', date: '2026-11-18T03:00:00Z', categories: ['Business', 'Finance'] },
];

jest.mock('../context/AuthContext', () => ({
  useAuth: () => ({
    user: { name: 'Reader' }, logout: jest.fn(), refreshFeed: jest.fn(), getRefreshStatus: jest.fn(),
    getFeed: async () => ({ articles }),
    selectedTopics: mockTopics,
    updatePreferences: (...args) => mockUpdatePreferences(...args),
  }),
}));
jest.mock('../context/TrustedPlatformsContext', () => {
  const platforms = [{ id: 'nst', name: 'New Straits Times' }, { id: 'fmt', name: 'Free Malaysia Today' }];
  return { useTrustedPlatforms: () => ({ platforms, isFollowing: () => true, toggleFollow: jest.fn(), resetToDefaults: jest.fn(), followedPlatforms: platforms }) };
});
jest.mock('../context/BookmarkContext', () => ({ useBookmarks: () => ({ isBookmarked: () => false, toggleBookmark: jest.fn() }) }));
jest.mock('../context/ReadArticlesContext', () => ({ useReadArticles: () => ({ isRead: () => false }) }));
jest.mock('../hooks/useOverscrollBounce', () => ({ useOverscrollBounce: () => {} }));
jest.mock('../components/DarkModeToggle', () => () => null);

beforeEach(() => {
  mockTopics = ['Politics'];
  mockUpdatePreferences.mockImplementation(async (topics) => { mockTopics = topics; });
  window.scrollTo = jest.fn();
  Element.prototype.scrollIntoView = jest.fn();
});

const titles = () => [...document.querySelectorAll('.article-card .article-title')].map(e => e.textContent);
const renderFeed = () => render(<MemoryRouter><FeedPage /></MemoryRouter>);

test('News For You shows only articles in the selected interests', async () => {
  renderFeed();
  await waitFor(() => expect(titles()).toEqual(['Parliament passes budget']));
});

test('changing interests updates News For You immediately and returns to it', async () => {
  const { rerender } = renderFeed();
  await waitFor(() => expect(titles()).toEqual(['Parliament passes budget']));
  fireEvent.click(screen.getByText('Sports'));            // browse another category first
  await waitFor(() => expect(titles()).toEqual(['Harimau Malaya wins final']));
  fireEvent.click(screen.getByTitle('Edit interests'));
  const editor = document.querySelector('.topic-editor-grid');
  fireEvent.click(within(editor).getByText('Politics'));  // remove Politics
  fireEvent.click(within(editor).getByText('Finance'));   // add Finance
  fireEvent.click(screen.getByText('Save Changes'));
  await waitFor(() => expect(mockUpdatePreferences).toHaveBeenCalledWith(['Finance']));
  rerender(<MemoryRouter><FeedPage /></MemoryRouter>);   // context now provides the new interests
  await waitFor(() => expect(titles()).toEqual(['Ringgit strengthens']));
  expect(document.querySelector('.sidebar-item.active').textContent).toContain('News For You');
});

test('with no interests, News For You shows all news', async () => {
  mockTopics = [];
  renderFeed();
  await waitFor(() => expect(titles()).toHaveLength(3));
});
