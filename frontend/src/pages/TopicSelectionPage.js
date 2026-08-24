import React, { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { useNavigate } from 'react-router-dom';
import { TOPICS } from '../constants/topics';
import './TopicSelectionPage.css';

const TopicSelectionPage = () => {
  const [selectedTopics, setSelectedTopics] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const navigate = useNavigate();
  const { completeTopicSelection } = useAuth();

  const handleToggleTopic = (topic) => {
    setSelectedTopics(prev =>
      prev.includes(topic)
        ? prev.filter(t => t !== topic)
        : [...prev, topic]
    );
  };

  const handleContinue = async () => {
    if (selectedTopics.length === 0) {
      alert('Please select at least one topic');
      return;
    }
    setLoading(true);
    setError('');

    try {
      // Persist to the backend so this is remembered for future logins and
      // the topic-selection page is skipped automatically next time.
      await completeTopicSelection(selectedTopics);
      navigate('/feed');
    } catch (err) {
      setError('Failed to save your interests. Please try again.');
      setLoading(false);
    }
  };

  return (
    <div className="topic-selection-container">
      <div className="topic-selection-box">
        <div className="topic-header">
          <h1><span className="heading-icon">🎯</span> Select Your Interests</h1>
          <p>Choose topics you'd like to read about</p>
        </div>

        <div className="topics-grid">
          {TOPICS.map(topic => (
            <button
              key={topic}
              className={`topic-button ${selectedTopics.includes(topic) ? 'selected' : ''}`}
              onClick={() => handleToggleTopic(topic)}
            >
              <span className="topic-checkbox">
                {selectedTopics.includes(topic) ? '✓' : '+'}
              </span>
              <span className="topic-label">{topic}</span>
            </button>
          ))}
        </div>

        {error && <p className="topic-error">{error}</p>}

        <div className="topic-footer">
          <p className="selection-count">{selectedTopics.length} topic(s) selected</p>
          <button
            className="continue-button"
            onClick={handleContinue}
            disabled={loading || selectedTopics.length === 0}
          >
            {loading ? (
              <><span className="btn-icon">⏳</span> Saving...</>
            ) : (
              <><span className="btn-icon">✨</span> Continue to Feed</>
            )}
          </button>
        </div>
      </div>
    </div>
  );
};

export default TopicSelectionPage;
