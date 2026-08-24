import React, { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { TOPICS, getTopicEmoji } from '../constants/topics';
import './SuggestionPanel.css';

const SuggestionPanel = () => {
  const { selectedTopics, updatePreferences } = useAuth();
  const [isEditing, setIsEditing] = useState(false);
  const [draftTopics, setDraftTopics] = useState(selectedTopics);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  const handleStartEdit = () => {
    setDraftTopics(selectedTopics);
    setError('');
    setIsEditing(true);
  };

  const handleCancelEdit = () => {
    setDraftTopics(selectedTopics);
    setError('');
    setIsEditing(false);
  };

  const handleToggleTopic = (topic) => {
    setDraftTopics(prev =>
      prev.includes(topic)
        ? prev.filter(t => t !== topic)
        : [...prev, topic]
    );
  };

  const handleSave = async () => {
    if (draftTopics.length === 0) {
      setError('Select at least one topic.');
      return;
    }
    setError('');
    setSaving(true);
    try {
      await updatePreferences(draftTopics);
      setIsEditing(false);
    } catch (err) {
      setError('Failed to save. Please try again.');
    } finally {
      setSaving(false);
    }
  };

  // Editing mode: show a topic picker grid the user can toggle and save.
  if (isEditing) {
    return (
      <div className="suggestion-panel">
        <div className="suggestion-header">
          <h3><span className="heading-icon">🎯</span> Edit Your Interests</h3>
          <p>Choose the topics you'd like to see in your feed:</p>
        </div>

        <div className="topic-editor-grid">
          {TOPICS.map(topic => (
            <button
              key={topic}
              className={`topic-editor-chip ${draftTopics.includes(topic) ? 'selected' : ''}`}
              onClick={() => handleToggleTopic(topic)}
              type="button"
            >
              <span className="tag-emoji">{getTopicEmoji(topic)}</span>
              <span className="tag-label">{topic}</span>
            </button>
          ))}
        </div>

        {error && <p className="suggestion-error">{error}</p>}

        <div className="topic-editor-actions">
          <button
            className="topic-editor-save"
            onClick={handleSave}
            disabled={saving || draftTopics.length === 0}
          >
            <span className="btn-icon">✓</span> {saving ? 'Saving...' : 'Save Changes'}
          </button>
          <button
            className="topic-editor-cancel"
            onClick={handleCancelEdit}
            disabled={saving}
          >
            <span className="btn-icon">✕</span> Cancel
          </button>
        </div>
      </div>
    );
  }

  // No topics selected yet - prompt the user to add some, still inline.
  if (!selectedTopics || selectedTopics.length === 0) {
    return (
      <div className="suggestion-panel">
        <div className="suggestion-header">
          <h3><span className="heading-icon">🎯</span> Personalize Your Feed</h3>
          <p>You haven't selected any interests yet.</p>
        </div>
        <button className="edit-topics-btn" onClick={handleStartEdit}>
          <span className="btn-icon">✏️</span> Choose Interests
        </button>
      </div>
    );
  }

  // Default (view) mode
  return (
    <div className="suggestion-panel">
      <div className="suggestion-header-row">
        <div className="suggestion-header">
          <h3><span className="heading-icon">🎯</span> Your Interests</h3>
          <p>Based on your selections:</p>
        </div>
        <button className="edit-topics-btn" onClick={handleStartEdit} title="Edit interests">
          <span className="btn-icon">✏️</span> Edit
        </button>
      </div>

      <div className="suggestion-tags">
        {selectedTopics.map((topic, index) => (
          <span key={index} className="suggestion-tag">
            <span className="tag-emoji">{getTopicEmoji(topic)}</span>
            <span className="tag-label">{topic}</span>
          </span>
        ))}
      </div>

      <div className="suggestion-message">
        <p>✨ Articles are personalized based on your interests. Click Edit above to change them anytime.</p>
      </div>
    </div>
  );
};

export default SuggestionPanel;
