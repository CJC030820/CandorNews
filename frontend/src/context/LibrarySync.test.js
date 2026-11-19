import React from 'react';
import { render, screen, act, waitFor } from '@testing-library/react';
import { BookmarkProvider, useBookmarks } from './BookmarkContext';
import { ReadArticlesProvider, useReadArticles } from './ReadArticlesContext';

// A fake server shared by "devices" (each device = its own localStorage).
let server;
const copy = () => JSON.parse(JSON.stringify(server));
const mockAuth = { user: { email: 'same@example.com' } };
// CRA resets mocks between tests, so implementations are set in beforeEach.
const fakeServer = () => Object.assign(mockAuth, {
  getLibrary: jest.fn(async () => copy()),
  importLibrary: jest.fn(async (lists) => {
    Object.entries(lists).forEach(([kind, items]) => items.forEach((item) => {
      if (!server[kind].some((x) => x.id === item.id)) server[kind].push(item);
    }));
    return copy();
  }),
  saveLibraryItem: jest.fn(async (kind, article) => {
    server[kind] = [article, ...server[kind].filter((x) => x.id !== article.id)];
  }),
  removeLibraryItem: jest.fn(async (kind, id) => { server[kind] = server[kind].filter((x) => x.id !== id); }),
  clearLibrary: jest.fn(async (kind) => { server[kind] = []; }),
});
jest.mock('./AuthContext', () => ({ useAuth: () => mockAuth }));

let api;
const Probe = () => {
  api = { ...useBookmarks(), ...useReadArticles() };
  return <p>{`b:${api.bookmarks.map((a) => a.id).join(',')} h:${api.history.map((a) => a.id).join(',')}`}</p>;
};
const openDevice = () => render(<BookmarkProvider><ReadArticlesProvider><Probe /></ReadArticlesProvider></BookmarkProvider>);

beforeEach(() => {
  server = { bookmarks: [], history: [] };
  localStorage.clear();
  fakeServer();
});

test('records saved on the PC show on the phone with the same email', async () => {
  const pc = openDevice();
  await waitFor(() => expect(mockAuth.importLibrary).toHaveBeenCalledTimes(2));
  act(() => { api.addBookmark({ id: 'a1', title: 'Budget' }); api.markAsRead({ id: 'a2', title: 'Ringgit' }); });
  await waitFor(() => expect(server.history).toHaveLength(1));
  expect(server.bookmarks.map((a) => a.id)).toEqual(['a1']);
  pc.unmount();

  localStorage.clear(); // a different device
  openDevice();
  await waitFor(() => expect(screen.getByText('b:a1 h:a2')).toBeInTheDocument());
});

test('a device that already had records adds them to the account once', async () => {
  server.bookmarks = [{ id: 'server', savedAt: '2026-11-18T00:00:00Z' }];
  localStorage.setItem('bookmarkedArticles:same@example.com', JSON.stringify([{ id: 'phone', savedAt: '2026-11-17T00:00:00Z' }]));
  const first = openDevice();
  await waitFor(() => expect(screen.getByText(/b:server,phone/)).toBeInTheDocument());
  first.unmount();

  openDevice();
  await waitFor(() => expect(mockAuth.getLibrary).toHaveBeenCalled());
  expect(mockAuth.importLibrary).toHaveBeenCalledTimes(2); // not again on the second visit
});

test('removing and clearing are sent to the account', async () => {
  server.bookmarks = [{ id: 'x' }];
  server.history = [{ id: 'y' }, { id: 'z' }];
  openDevice();
  await waitFor(() => expect(screen.getByText('b:x h:y,z')).toBeInTheDocument());
  act(() => { api.removeBookmark('x'); api.clearHistory(); });
  expect(screen.getByText('b: h:')).toBeInTheDocument();
  await waitFor(() => expect(server).toEqual({ bookmarks: [], history: [] }));
});

test('when the server cannot be reached, this device keeps its own copy', async () => {
  localStorage.setItem('librarySynced:same@example.com:history', '1');
  localStorage.setItem('librarySynced:same@example.com:bookmarks', '1');
  localStorage.setItem('readArticleHistory:same@example.com', JSON.stringify([{ id: 'local' }]));
  mockAuth.getLibrary.mockRejectedValueOnce(new Error('offline')).mockRejectedValueOnce(new Error('offline'));
  openDevice();
  await waitFor(() => expect(mockAuth.getLibrary).toHaveBeenCalledTimes(2));
  expect(screen.getByText('b: h:local')).toBeInTheDocument();
});
