// Shared topic list + emoji mapping used by the Topic Selection page and
// the in-feed topic editor (SuggestionPanel), so both stay in sync.

export const TOPICS = [
  'Malaysia', 'Politics', 'Business', 'Health',
  'Sports', 'Entertainment', 'Education', 'Lifestyle',
  'Technology', 'Property', 'World', 'Crime'
];

export const TOPIC_EMOJIS = {
  'Malaysia': '🇲🇾',
  'Politics': '🏛️',
  'Business': '💼',
  'Health': '🏥',
  'Sports': '🏆',
  'Entertainment': '🎬',
  'Education': '📚',
  'Lifestyle': '🏙️',
  'Technology': '💻',
  'Property': '🏠',
  'World': '🌍',
  'Crime': '🚨'
};

export const getTopicEmoji = (topic) => TOPIC_EMOJIS[topic] || '📰';
