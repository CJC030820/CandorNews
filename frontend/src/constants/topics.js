// Shared topic list + emoji mapping used by the Topic Selection page and
// the in-feed topic editor (SuggestionPanel), so both stay in sync.

export const TOPICS = [
  'Politics', 'Business', 'Health', 'Sports', 'Entertainment',
  'Technology', 'AI', 'Finance', 'Crime', 'Local Malaysia News', 'General'
];

export const REMOVED_TOPICS = new Set([
  'Education', 'Lifestyle', 'Property', 'Malaysia', 'World'
]);

export const normalizeTopics = (topics = []) => [...new Set(topics)]
  .filter((topic) => TOPICS.includes(topic) && !REMOVED_TOPICS.has(topic));


