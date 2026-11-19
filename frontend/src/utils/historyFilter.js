// Filters for saved article lists (reading history, bookmarks):
// keyword, time (viewed / saved) and category.

export const TIME_OPTIONS = [
  { value: 'all', label: 'All time' },
  { value: 'today', label: 'Today' },
  { value: 'yesterday', label: 'Yesterday' },
  { value: '7d', label: 'Last 7 days' },
  { value: '30d', label: 'Last 30 days' },
  { value: 'date', label: 'Pick a date' },
];

export const EMPTY_FILTERS = { query: '', time: 'all', date: '', category: 'all' };

export const categoriesOf = (article = {}) =>
  (article.categories && article.categories.length ? article.categories : [article.category]).filter(Boolean);

// Categories present in the list, most common first.
export const historyCategories = (items = []) => {
  const counts = new Map();
  items.forEach((a) => categoriesOf(a).forEach((c) => counts.set(c, (counts.get(c) || 0) + 1)));
  return [...counts.entries()].sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0])).map(([c]) => c);
};

const startOfDay = (d) => new Date(d.getFullYear(), d.getMonth(), d.getDate());

// "2026-11-19" (from <input type="date">) -> local midnight
const parseLocalDate = (value) => {
  const [y, m, d] = (value || '').split('-').map(Number);
  return y && m && d ? new Date(y, m - 1, d) : null;
};

export const matchesTime = (when, time, date, now = new Date()) => {
  if (!time || time === 'all') return true;
  const at = new Date(when);
  if (!when || Number.isNaN(at.getTime())) return false;
  const today = startOfDay(now);
  const day = 24 * 60 * 60 * 1000;
  switch (time) {
    case 'today': return at >= today;
    case 'yesterday': return at >= new Date(today - day) && at < today;
    case '7d': return at >= new Date(today - 6 * day);
    case '30d': return at >= new Date(today - 29 * day);
    case 'date': {
      const picked = parseLocalDate(date);
      if (!picked) return true;
      return at >= picked && at < new Date(picked.getTime() + day);
    }
    default: return true;
  }
};

// timeOf: which timestamp the time filter uses (viewed for history, saved for bookmarks).
export const filterArticles = (items = [], filters = EMPTY_FILTERS, now = new Date(), timeOf = (a) => a.readAt) => {
  const { query = '', time = 'all', date = '', category = 'all' } = filters;
  const q = query.trim().toLowerCase();
  return items.filter((a) => {
    if (q && ![a.title, a.source, a.description].some((t) => (t || '').toLowerCase().includes(q))) return false;
    if (category !== 'all' && !categoriesOf(a).includes(category)) return false;
    return matchesTime(timeOf(a), time, date, now);
  });
};

export const filterHistory = (history, filters, now) => filterArticles(history, filters, now, (a) => a.readAt);

// Bookmarks: when it was saved; older bookmarks fall back to the publish date.
export const bookmarkTime = (a) => a.savedAt || a.rawDate || (Number.isNaN(Date.parse(a.date)) ? null : a.date);
export const filterBookmarks = (bookmarks, filters, now) => filterArticles(bookmarks, filters, now, bookmarkTime);
