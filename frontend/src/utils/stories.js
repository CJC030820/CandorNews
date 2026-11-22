// One card per story. When several followed publishers report the same story
// (the server gives their articles the same storyId), the feed shows the
// version with the highest trust score (the earliest one on a tie) and names
// the other publishers on the card.
//
// `articles` are the ones to show (after filters and search); `pool` holds
// every version the reader could see (followed publishers), so a card can name
// all of them even when only one matched a search.
const keyOf = (article) => article.storyId || article.id;

const better = (a, b) => {
  const scoreA = a.trustScore ?? -1;
  const scoreB = b.trustScore ?? -1;
  if (scoreA !== scoreB) return scoreA > scoreB ? a : b;
  return new Date(a.rawDate || a.date) <= new Date(b.rawDate || b.date) ? a : b;
};

export const combineStories = (articles = [], pool = articles) => {
  const versionsOf = new Map();
  [...pool, ...articles].forEach((article) => {
    const key = keyOf(article);
    const list = versionsOf.get(key) || [];
    if (!list.some((v) => v.id === article.id)) list.push(article);
    versionsOf.set(key, list);
  });

  const leads = new Map();   // story -> best matching version, in order of first appearance
  articles.forEach((article) => {
    const key = keyOf(article);
    leads.set(key, leads.has(key) ? better(leads.get(key), article) : article);
  });

  return [...leads.entries()].map(([key, lead]) => {
    const versions = versionsOf.get(key) || [lead];
    if (versions.length < 2) return lead;
    const others = [];
    versions.forEach((v) => {
      if (v.id !== lead.id && v.source !== lead.source && !others.some((o) => o.source === v.source)) {
        others.push({ id: v.id, source: v.source, trustScore: v.trustScore });
      }
    });
    return { ...lead, otherVersions: others, versionIds: versions.map((v) => v.id) };
  });
};
