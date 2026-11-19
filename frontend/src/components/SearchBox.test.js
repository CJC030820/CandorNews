import React, { useState } from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter, Routes, Route, useLocation } from 'react-router-dom';
import SearchBox from './SearchBox';

const mockAuth = { user: { email: 'r@example.com' } };
jest.mock('../context/AuthContext', () => ({ useAuth: () => mockAuth }));

let where;
const Where = () => { where = useLocation().pathname; return null; };
const Harness = ({ start = '/feed' }) => {
  const [q, setQ] = useState('');
  return (
    <MemoryRouter initialEntries={[start]}>
      <SearchBox value={q} onChange={setQ} />
      <Routes><Route path="*" element={<Where />} /></Routes>
      <output data-testid="query">{q}</output>
    </MemoryRouter>
  );
};

beforeEach(() => {
  mockAuth.suggestKeywords = jest.fn(async (q) => (q
    ? { kind: 'completions', query: { text: q.trim(), count: q === 'zzz' ? 0 : 11 },
        suggestions: q === 'zzz' ? [] : [{ text: 'climate', count: 9 }, { text: 'climate change', count: 4 }] }
    : { kind: 'trending', query: null, suggestions: [{ text: 'floods', count: 30 }, { text: 'budget', count: 12 }] }));
});

const box = () => screen.getByRole('combobox', { name: 'Search articles' });
const options = () => screen.queryAllByRole('option').map((o) => o.textContent);

test('an empty box shows trending topics', async () => {
  render(<Harness />);
  fireEvent.focus(box());
  await waitFor(() => expect(options()).toEqual(['floods30 articles', 'budget12 articles']));
  expect(screen.getByText('Trending now')).toBeInTheDocument();
  expect(mockAuth.suggestKeywords).toHaveBeenCalledWith('');
});

test('what the user typed comes first, then completions with the typed part plain', async () => {
  render(<Harness />);
  fireEvent.change(box(), { target: { value: 'cli' } });
  await waitFor(() => expect(options()).toHaveLength(3));
  expect(mockAuth.suggestKeywords).toHaveBeenLastCalledWith('cli');
  expect(options()[0]).toBe('Search “cli”11 articles');
  expect(screen.getAllByRole('option')[2].querySelector('strong').textContent).toBe('mate change');
});

test('a search with no articles says so', async () => {
  render(<Harness />);
  fireEvent.change(box(), { target: { value: 'zzz' } });
  await waitFor(() => expect(options()).toEqual(['Search “zzz”no articles']));
});

test('keyboard: arrows move, Enter picks, Escape closes', async () => {
  render(<Harness />);
  fireEvent.change(box(), { target: { value: 'cli' } });
  await waitFor(() => expect(options()).toHaveLength(3));
  fireEvent.keyDown(box(), { key: 'ArrowDown' });
  fireEvent.keyDown(box(), { key: 'ArrowDown' });
  fireEvent.keyDown(box(), { key: 'ArrowDown' });
  expect(screen.getAllByRole('option')[2]).toHaveAttribute('aria-selected', 'true');
  fireEvent.keyDown(box(), { key: 'Enter' });
  expect(screen.getByTestId('query').textContent).toBe('climate change');
  expect(options()).toEqual([]);

  fireEvent.change(box(), { target: { value: 'cl' } });
  await waitFor(() => expect(options()).toHaveLength(3));
  fireEvent.keyDown(box(), { key: 'Escape' });
  expect(options()).toEqual([]);
});

test('clicking a suggestion on another page searches it on the feed', async () => {
  render(<Harness start="/history" />);
  fireEvent.change(box(), { target: { value: 'cli' } });
  await waitFor(() => expect(options()).toHaveLength(3));
  fireEvent.mouseDown(screen.getAllByRole('option')[1]);
  expect(screen.getByTestId('query').textContent).toBe('climate');
  expect(where).toBe('/feed');
});

test('logged-out visitors get no suggestions', async () => {
  const saved = mockAuth.user;
  mockAuth.user = null;
  render(<Harness />);
  fireEvent.change(box(), { target: { value: 'cli' } });
  await new Promise((r) => setTimeout(r, 250));
  expect(mockAuth.suggestKeywords).not.toHaveBeenCalled();
  mockAuth.user = saved;
});
