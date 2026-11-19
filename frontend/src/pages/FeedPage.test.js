import React from 'react';
import { render, screen, fireEvent, waitFor, within, act } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import FeedPage from './FeedPage';

let mockTopics = ['Politics'];
let mockFeedArticles = null;
const mockUpdatePreferences = jest.fn();
const articles = [
  { id: '1', title: 'Parliament passes budget', source: 'New Straits Times', date: '2026-11-18T01:00:00Z', categories: ['Politics'] },
  { id: '2', title: 'Harimau Malaya wins final', source: 'New Straits Times', date: '2026-11-18T02:00:00Z', categories: ['Sports'] },
  { id: '3', title: 'Ringgit strengthens', source: 'Free Malaysia Today', date: '2026-11-18T03:00:00Z', categories: ['Business', 'Finance'] },
];

// Stable like the real context's useCallback, so the feed does not reload in a loop.
const mockGetFeed = async () => ({ articles: mockFeedArticles || articles });
const mockSearch = jest.fn();

jest.mock('../context/AuthContext', () => ({
  useAuth: () => ({
    user: { name: 'Reader' }, logout: jest.fn(), refreshFeed: jest.fn(), getRefreshStatus: jest.fn(),
    getFeed: mockGetFeed,
    searchArticles: (...args) => mockSearch(...args),
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
jest.mock('../components/DarkModeToggle', () => () => null);

beforeEach(() => {
  mockTopics = ['Politics'];
  mockFeedArticles = null;
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

const captureReload = () => {
  const spy = jest.spyOn(window, 'setInterval');
  return () => spy.mock.calls.filter(([, delay]) => delay === 60000).map(([fn]) => fn).pop();
};
const newStory = { id: '9', title: 'Breaking: new story', source: 'New Straits Times', date: '2026-11-18T09:00:00Z', categories: ['Politics'] };

test('background reload does not insert articles above a reader who scrolled down', async () => {
  mockTopics = [];
  const reloader = captureReload();
  renderFeed();
  await waitFor(() => expect(titles()).toHaveLength(3));
  Object.defineProperty(window, 'scrollY', { value: 1200, configurable: true });
  mockFeedArticles = [newStory, ...articles];
  await act(async () => { await reloader()(); });
  expect(titles()).toHaveLength(3);                       // list unchanged while reading
  fireEvent.click(await screen.findByText('1 new article'));
  expect(titles()[0]).toBe('Breaking: new story');
  expect(window.scrollTo).toHaveBeenCalledWith({ top: 0, left: 0, behavior: 'auto' });
  Object.defineProperty(window, 'scrollY', { value: 0, configurable: true });
});

test('background reload applies immediately when the reader is at the top', async () => {
  mockTopics = [];
  Object.defineProperty(window, 'scrollY', { value: 0, configurable: true });
  const reloader = captureReload();
  renderFeed();
  await waitFor(() => expect(titles()).toHaveLength(3));
  mockFeedArticles = [newStory, ...articles];
  await act(async () => { await reloader()(); });
  await waitFor(() => expect(titles()[0]).toBe('Breaking: new story'));
  expect(screen.queryByText(/new article/)).toBeNull();
});


test('search looks through all saved articles, beyond the latest batch and interests', async () => {
  mockSearch.mockResolvedValue({ articles: [
    { id: '9', title: 'Old budget debate recap', source: 'New Straits Times', date: '2026-05-01T01:00:00Z', categories: ['Business'] },
  ] });
  render(<MemoryRouter><FeedPage searchQuery="budget" /></MemoryRouter>);
  await waitFor(() => expect(titles()).toEqual(['Parliament passes budget', 'Old budget debate recap']));
  expect(mockSearch).toHaveBeenCalledWith('budget', 200);
  await waitFor(() => expect(document.querySelector('.feed-status')?.textContent).toBe('2 results from all saved articles'));
});

test('News For You can be switched to newest first', async () => {
  renderFeed();
  await waitFor(() => expect(titles()).toEqual(['Parliament passes budget']));
  fireEvent.change(screen.getByLabelText('Order of News For You'), { target: { value: 'newest' } });
  expect(screen.getByLabelText('Order of News For You').value).toBe('newest');
});
