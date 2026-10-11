// Shared topic list + emoji mapping used by the Topic Selection page and
// the in-feed topic editor (SuggestionPanel), so both stay in sync.

export const TOPICS = [
  'Politics', 'Business', 'Health', 'Sports', 'Entertainment',
  'Technology', 'AI', 'Finance', 'Crime', 'Local Malaysia News'
];

export const REMOVED_TOPICS = new Set([
  'Education', 'Lifestyle', 'Property', 'Malaysia', 'World', 'General'
]);

export const normalizeTopics = (topics = []) => [...new Set(topics)]
  .filter((topic) => TOPICS.includes(topic) && !REMOVED_TOPICS.has(topic));

export const TOPIC_EMOJIS = {
  'Politics': '🏛️',
  'Business': '💼',
  'Health': '🏥',
  'Sports': '🏆',
  'Entertainment': '🎬',
  'Technology': '💻',
  'AI': '🤖',
  'Finance': '💰',
  'Crime': '🚨',
  'Local Malaysia News': '🇲🇾'
};

export const getTopicEmoji = (topic) => TOPIC_EMOJIS[topic] || '📰';
