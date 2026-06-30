import React, { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import axios from 'axios';

const ProfilePage = () => {
  const { user, updatePreferences } = useAuth();
  const [preferredTopics, setPreferredTopics] = useState(user?.preferred_topics || []);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);

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

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    setSuccess(false);
    try {
      const updatedUser = await updatePreferences(preferredTopics);
      setSuccess(true);
      // Update local state
      setPreferredTopics(preferredTopics);
    } catch (err) {
      console.error('Error updating preferences:', err);
      setError('Failed to update preferences');
    } finally {
      setLoading(false);
    }
  };

  const toggleTopic = (topic) => {
    if (preferredTopics.includes(topic)) {
      setPreferredTopics(preferredTopics.filter(t => t !== topic));
    } else {
      setPreferredTopics([...preferredTopics, topic]);
    }
  };

  return (
    <div className="profile-page">
      <h2>Profile</h2>
      {user && (
        <>
          <p>Name: {user.name}</p>
          <p>Email: {user.email}</p>
        </>
      )}
      <div className="preferences-section">
        <h3>Preferred Topics</h3>
        <form onSubmit={handleSubmit}>
          <div className="topics-grid">
            {TOPICS.map(topic => (
              <div key={topic} className={`topic-item ${preferredTopics.includes(topic) ? 'selected' : ''}`}>
                <label>
                  <input
                    type="checkbox"
                    checked={preferredTopics.includes(topic)}
                    onChange={() => toggleTopic(topic)}
                  />
                  {topic}
                </label>
              </div>
            ))}
          </div>
          <button type="submit" disabled={loading}>
            {loading ? 'Saving...' : 'Save Preferences'}
          </button>
        </form>
        {error && <p className="error">{error}</p>}
        {success && <p className="success">Preferences saved successfully!</p>}
      </div>
    </div>
  );
};

export default ProfilePage;