// One card per story, and one card per developing story.
//
// The server marks articles that report the same event with one storyId (one
// version per publisher), and a developing story's updates over time with one
// threadId. The feed shows a single card for each thread: its latest update,
// as told by the version with the highest trust score (the earliest one on a
// tie). The card names the other publishers of that update and says how many
// updates the developing story has.
//
// `articles` are the ones to show (after filters and search); `pool` holds
// every article the reader could see (followed publishers), so a card can name
// all versions and count all updates even when only one article matched.
const storyKey = (article) => article.storyId || article.id;
const threadKey = (article) => article.threadId || storyKey(article);
const time = (article) => new Date(article.rawDate || article.date).getTime();

const better = (a, b) => {
  const scoreA = a.trustScore ?? -1;
  const scoreB = b.trustScore ?? -1;
  if (scoreA !== scoreB) return scoreA > scoreB ? a : b;
  return time(a) <= time(b) ? a : b;
};

const groupBy = (items, keyOf) => {
  const groups = new Map();
  items.forEach((item) => {
    const key = keyOf(item);
    const list = groups.get(key) || [];
    if (!list.some((other) => other.id === item.id)) list.push(item);
    groups.set(key, list);
  });
  return groups;
};

export const combineStories = (articles = [], pool = articles) => {
  const visible = groupBy([...pool, ...articles], threadKey);   // thread -> every visible article
  const matched = groupBy(articles, threadKey);                 // thread -> articles to show, in order

  return [...matched.entries()].map(([key, hits]) => {
    const threadArticles = visible.get(key) || hits;
    const stories = groupBy(threadArticles, storyKey);
    // The latest update among the matching articles leads the card.
    const hitStories = groupBy(hits, storyKey);
    const firstReport = (versions) => Math.min(...versions.map(time));
    const [latestKey, latestHits] = [...hitStories.entries()]
      .reduce((a, b) => (firstReport(b[1]) > firstReport(a[1]) ? b : a));
    const lead = latestHits.reduce(better);

    const others = [];
    (stories.get(latestKey) || []).forEach((v) => {
      if (v.id !== lead.id && v.source !== lead.source && !others.some((o) => o.source === v.source)) {
        others.push({ id: v.id, source: v.source, trustScore: v.trustScore });
      }
    });
    // The server counts every update, including older ones not loaded in the feed.
    const updates = Math.max(stories.size, ...threadArticles.map((a) => a.threadUpdates || 0));
    if (!others.length && updates < 2) return lead;
    const card = { ...lead, versionIds: threadArticles.map((a) => a.id) };
    if (others.length) card.otherVersions = others;
    if (updates > 1) card.updateCount = updates;
    return card;
  });
};
