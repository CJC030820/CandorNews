import { buildProfile, keywordsOf, rankForYou, scoreArticle } from './personalRanking';

const now = new Date('2026-11-19T12:00:00Z').getTime();
const hoursAgo = (h) => new Date(now - h * 3600000).toISOString();
const ids = (list) => list.map((a) => a.id);

const history = [
  { id: 'h1', title: 'Flood victims in Kelantan receive aid', source: 'Bernama', categories: ['Local Malaysia News'] },
  { id: 'h2', title: 'More flood relief centres opened', source: 'Bernama', categories: ['Local Malaysia News'] },
  { id: 'h3', title: 'Kelantan flood waters rise again', source: 'New Straits Times', categories: ['Local Malaysia News'] },
];

test('keywords skip short and common words', () => {
  expect(keywordsOf("Malaysia's flood relief: aid for the victims")).toEqual(['flood', 'relief', 'victim']);
  expect(keywordsOf('Flash floods hit Penang')).toEqual(['flash', 'flood', 'penang']);
});

test('with little history the order stays newest first', () => {
  const articles = [{ id: 'a', rawDate: hoursAgo(5) }, { id: 'b', rawDate: hoursAgo(1) }];
  const result = rankForYou(articles, history.slice(0, 1), [], now);
  expect(result.personalised).toBe(false);
  expect(ids(result.articles)).toEqual(['b', 'a']);
});

test('a story close to what the reader follows moves above a slightly newer unrelated one', () => {
  const articles = [
    { id: 'football', title: 'Harimau Malaya friendly fixture announced', source: 'Free Malaysia Today', categories: ['Sports'], rawDate: hoursAgo(1) },
    { id: 'flood', title: 'Flood relief reaches Kelantan villages', source: 'Bernama', categories: ['Local Malaysia News'], rawDate: hoursAgo(3) },
  ];
  const { articles: ranked, personalised } = rankForYou(articles, history, [], now);
  expect(personalised).toBe(true);
  expect(ids(ranked)).toEqual(['flood', 'football']);
  expect(ranked[0].forYouReason).toMatch(/flood|kelantan/i);
  expect(ranked[1].forYouReason).toBeUndefined();
});

test('freshness still matters: a week-old match does not beat today', () => {
  const articles = [
    { id: 'old', title: 'Flood relief Kelantan update', source: 'Bernama', categories: ['Local Malaysia News'], rawDate: hoursAgo(24 * 7) },
    { id: 'new', title: 'Parliament sitting resumes', source: 'Free Malaysia Today', categories: ['Politics'], rawDate: hoursAgo(1) },
  ];
  expect(ids(rankForYou(articles, history, [], now).articles)).toEqual(['new', 'old']);
});

test('already-read stories move down and bookmarks count double', () => {
  const profile = buildProfile(history, [{ id: 'b1', title: 'Budget surplus', source: 'Bernama', categories: ['Business'] }]);
  expect(profile.categories.get('Business')).toBe(2);
  const article = { id: 'h1', title: 'Flood victims in Kelantan receive aid', source: 'Bernama', categories: ['Local Malaysia News'], rawDate: hoursAgo(1) };
  const read = scoreArticle(article, profile, now).score;
  const unread = scoreArticle({ ...article, id: 'other' }, profile, now).score;
  expect(read).toBeLessThan(unread);
});

test('a category almost every story has does not count as a reason', () => {
  const local = (id, title, h) => ({ id, title, source: 'Bernama', categories: ['Local Malaysia News'], rawDate: hoursAgo(h) });
  const articles = [local('a', 'Road works begin in Ipoh', 1), local('b', 'Durian season starts early', 2),
    local('c', 'New bus routes for Penang', 3), { id: 'd', title: 'Stocks edge higher', source: 'Bernama', categories: ['Business'], rawDate: hoursAgo(4) }];
  // Reads local news 2 times in 3, while 3 in 4 feed stories are local.
  const mixed = [...history.slice(0, 2), { id: 'h4', title: 'Bursa closes higher', source: 'Bernama', categories: ['Business'] }];
  const ranked = rankForYou(articles, mixed, [], now).articles;
  expect(ranked.filter((a) => /Local Malaysia News/.test(a.forYouReason || ''))).toHaveLength(0);
});
