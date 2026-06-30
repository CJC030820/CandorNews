import React, { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { useNavigate } from 'react-router-dom';

const TOPICS = [
  "Technology",
  "Business",
  "Politics",
  "Sports",
  "Health",
  "AI",
  "Local Malaysia News",
  "Entertainment",
  "Finance"
];

const TopicSelectionPage = () => {
  const [selectedTopics, setSelectedTopics] = useState([]);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const { updatePreferences } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    try {
      await updatePreferences(selectedTopics);
      navigate('/feed');
    } catch (err) {
      setError('Failed to save preferences');
    } finally {
      setLoading(false);
    }
  };

  const toggleTopic = (topic) => {
    if (selectedTopics.includes(topic)) {
      setSelectedTopics(selectedTopics.filter(t => t !== topic));
    } else {
      setSelectedTopics([...selectedTopics, topic]);
    }
  };

  return (
    <div className="topic-selection-page">
      <h2>Select Your Interests</h2>
      <p>Choose topics you're interested in to personalize your news feed.</p>
      <form onSubmit={handleSubmit}>
        <div className="topics-grid">
          {TOPICS.map(topic => (
            <div key={topic} className={`topic-item ${selectedTopics.includes(topic) ? 'selected' : ''}`}>
              <label>
                <input
                  type="checkbox"
                  checked={selectedTopics.includes(topic)}
                  onChange={() => toggleTopic(topic)}
                />
                {topic}
              </label>
            </div>
          ))}
        </div>
        <button type="submit" disabled={loading}>
          {loading ? 'Saving...' : 'Save and Continue'}
        </button>
      </form>
      {error && <p className="error">{error}</p>}
    </div>
  );
};

export default TopicSelectionPage;