// Personal ranking for "News For You".
//
// A reading profile is built from what the user read (History) and saved
// (Bookmarks, counted double): which categories and publishers they read most
// and which words appear in those headlines. Each article gets a score that
// mixes how well it matches the profile with how new it is, so fresh stories
// still come first while stories closer to the reader's habits move up.
// Articles already read move down. Every score comes with a short reason.

const STOP_WORDS = new Set(('about after again against also among amid been before being between both could ' +
  'during each from have here into just more most must over said says should some still such than that their ' +
  'them then there these they this those through under until very were what when where which while will with ' +
  'would year years your malaysia malaysian news says say new today amid after over').split(' '));

const PROFILE_SIZE = 150;      // most recent history + bookmark entries used
const MIN_SIGNALS = 3;         // below this, keep the plain newest-first order
const HALF_LIFE_HOURS = 18;    // freshness halves every 18 hours
const WEIGHTS = { category: 0.35, publisher: 0.1, keywords: 0.55 };
const FRESHNESS_SHARE = 0.55;  // share of the final score from freshness
const READ_PENALTY = 0.5;
const MIN_WORD_WEIGHT = 2;

export const categoriesOf = (a = {}) =>
  (a.categories && a.categories.length ? a.categories : [a.category]).filter(Boolean);

export const keywordsOf = (title = '') =>
  [...new Set((title.toLowerCase().match(/[a-z][a-z'-]{3,}/g) || [])
    .map((w) => w.replace(/'s$/, ''))
    // "floods" and "flood" count as the same word.
    .map((w) => (w.length > 4 && /[^s]s$/.test(w) ? w.slice(0, -1) : w))
  )].filter((w) => !STOP_WORDS.has(w));

const add = (map, key, by) => map.set(key, (map.get(key) || 0) + by);
// How much more the reader picks a category/publisher than the feed has it
// (0 = no more than average, 1 = only reads that). Without feed numbers,
// the reader's own share is used.
const lift = (map, total, keys, feed) => Math.max(0, ...keys.map((k) => {
  const mine = total ? (map.get(k) || 0) / total : 0;
  const common = feed ? feed.get(k) || 0 : 0;
  return common >= 1 ? 0 : Math.max(0, (mine - common) / (1 - common));
}));

const feedShares = (articles, keysOf) => {
  const counts = new Map();
  articles.forEach((a) => keysOf(a).forEach((k) => add(counts, k, 1)));
  counts.forEach((n, k) => counts.set(k, n / Math.max(1, articles.length)));
  return counts;
};

export const buildProfile = (history = [], bookmarks = []) => {
  const categories = new Map();
  const publishers = new Map();
  const words = new Map();
  let total = 0;
  const signals = [...bookmarks.slice(0, PROFILE_SIZE).map((a) => [a, 2]), ...history.slice(0, PROFILE_SIZE).map((a) => [a, 1])];
  signals.forEach(([a, weight]) => {
    total += weight;
    categoriesOf(a).forEach((c) => add(categories, c, weight));
    if (a.source) add(publishers, a.source, weight);
    keywordsOf(a.title).forEach((w) => add(words, w, weight));
  });
  const topWord = Math.max(1, ...words.values());
  return { categories, publishers, words, total, topWord, signals: signals.length,
    readIds: new Set(history.map((a) => String(a.id))) };
};

const freshness = (article, now) => {
  const ageHours = Math.max(0, (now - new Date(article.rawDate || article.date)) / 3600000);
  return Number.isFinite(ageHours) ? 0.5 ** (ageHours / HALF_LIFE_HOURS) : 0;
};

export const scoreArticle = (article, profile, now = Date.now(), feed = {}) => {
  const cats = categoriesOf(article);
  const categoryMatch = lift(profile.categories, profile.total, cats, feed.categories);
  const publisherMatch = lift(profile.publishers, profile.total, [article.source], feed.publishers);
  // Only words that came up in at least two stories (or one bookmark) count,
  // so one-off words like "public" do not drive the order.
  const matched = keywordsOf(article.title)
    .filter((w) => (profile.words.get(w) || 0) >= MIN_WORD_WEIGHT)
    .sort((x, y) => profile.words.get(y) - profile.words.get(x));
  const keywordMatch = Math.min(1, matched.reduce((sum, w) => sum + profile.words.get(w) / profile.topWord, 0));
  const affinity = WEIGHTS.category * categoryMatch + WEIGHTS.publisher * publisherMatch + WEIGHTS.keywords * keywordMatch;
  let score = FRESHNESS_SHARE * freshness(article, now) + (1 - FRESHNESS_SHARE) * affinity;
  // A story counts as read when any publisher's version of it was read.
  const ids = article.versionIds && article.versionIds.length ? article.versionIds : [article.id];
  if (ids.some((id) => profile.readIds.has(String(id)))) score *= READ_PENALTY;

  let reason = null;
  if (matched.length && keywordMatch >= 0.3) reason = `Similar to stories you read about "${matched[0]}"`;
  else if (categoryMatch >= 0.3) {
    const top = [...cats].sort((x, y) => (profile.categories.get(y) || 0) - (profile.categories.get(x) || 0))[0];
    reason = `You often read ${top}`;
  }
  return { score, reason };
};

// Returns the articles in personal order, each with `forYouReason` when there
// is a clear reason. Falls back to newest first when there is little history.
export const rankForYou = (articles, history, bookmarks, now = Date.now()) => {
  const newest = [...articles].sort((a, b) => new Date(b.rawDate) - new Date(a.rawDate));
  const profile = buildProfile(history, bookmarks);
  if (profile.signals < MIN_SIGNALS) return { articles: newest, personalised: false };
  const feed = { categories: feedShares(articles, categoriesOf), publishers: feedShares(articles, (a) => [a.source]) };
  const ranked = newest
    .map((a, index) => ({ a, index, ...scoreArticle(a, profile, now, feed) }))
    .sort((x, y) => y.score - x.score || x.index - y.index)
    .map(({ a, reason }) => (reason ? { ...a, forYouReason: reason } : a));
  return { articles: ranked, personalised: true };
};
