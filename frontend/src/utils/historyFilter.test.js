import { bookmarkTime, filterBookmarks, filterHistory, historyCategories, matchesTime } from './historyFilter';

const now = new Date(2026, 10, 19, 15, 0); // 19 Nov 2026, 3 pm local
const at = (d, h = 10) => new Date(2026, 10, d, h, 0).toISOString();
const history = [
  { id: 1, title: 'Budget passed in Parliament', source: 'New Straits Times', categories: ['Politics'], readAt: at(19) },
  { id: 2, title: 'Ringgit strengthens', source: 'Free Malaysia Today', categories: ['Business', 'Finance'], readAt: at(18) },
  { id: 3, title: 'Harimau Malaya win', source: 'BERNAMA - English Version', category: 'Sports', readAt: at(14) },
  { id: 4, title: 'Old politics story', source: 'New Straits Times', categories: ['Politics'], readAt: at(1) },
];
const ids = (list) => list.map((a) => a.id);

test('time options', () => {
  expect(ids(filterHistory(history, { time: 'today' }, now))).toEqual([1]);
  expect(ids(filterHistory(history, { time: 'yesterday' }, now))).toEqual([2]);
  expect(ids(filterHistory(history, { time: '7d' }, now))).toEqual([1, 2, 3]);
  expect(ids(filterHistory(history, { time: '30d' }, now))).toEqual([1, 2, 3, 4]);
  expect(ids(filterHistory(history, { time: 'all' }, now))).toEqual([1, 2, 3, 4]);
});

test('a picked date matches the whole local day; no date picked shows all', () => {
  expect(ids(filterHistory(history, { time: 'date', date: '2026-11-14' }, now))).toEqual([3]);
  expect(ids(filterHistory(history, { time: 'date', date: '' }, now))).toEqual([1, 2, 3, 4]);
});

test('keyword matches headline or publisher, case-insensitive', () => {
  expect(ids(filterHistory(history, { query: 'ringgit' }, now))).toEqual([2]);
  expect(ids(filterHistory(history, { query: 'bernama' }, now))).toEqual([3]);
});

test('category uses any of the article categories', () => {
  expect(ids(filterHistory(history, { category: 'Finance' }, now))).toEqual([2]);
  expect(ids(filterHistory(history, { category: 'Sports' }, now))).toEqual([3]);
});

test('filters combine', () => {
  expect(ids(filterHistory(history, { category: 'Politics', time: '7d' }, now))).toEqual([1]);
  expect(ids(filterHistory(history, { category: 'Politics', query: 'old' }, now))).toEqual([4]);
});

test('category list is most common first', () => {
  expect(historyCategories(history)).toEqual(['Politics', 'Business', 'Finance', 'Sports']);
});

test('entries without a valid time only appear under All time', () => {
  expect(matchesTime(undefined, 'today', '', now)).toBe(false);
  expect(matchesTime(undefined, 'all', '', now)).toBe(true);
});

test('bookmarks filter by saved time, falling back to the publish date', () => {
  const bookmarks = [
    { id: 'a', title: 'Saved today', savedAt: at(19), rawDate: at(2) },
    { id: 'b', title: 'Old bookmark', rawDate: at(18) },
    { id: 'c', title: 'Relative date only', date: '20 minutes ago' },
  ];
  expect(bookmarkTime(bookmarks[0])).toBe(bookmarks[0].savedAt);
  expect(ids(filterBookmarks(bookmarks, { time: 'today' }, now))).toEqual(['a']);
  expect(ids(filterBookmarks(bookmarks, { time: 'yesterday' }, now))).toEqual(['b']);
  expect(ids(filterBookmarks(bookmarks, { time: 'all' }, now))).toEqual(['a', 'b', 'c']);
});
