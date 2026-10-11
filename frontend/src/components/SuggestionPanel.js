import React, { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { TOPICS, getTopicEmoji, normalizeTopics } from '../constants/topics';
import './SuggestionPanel.css';

const SuggestionPanel = () => {
  const { selectedTopics, updatePreferences } = useAuth();
  const [isEditing, setIsEditing] = useState(false);
  const [draftTopics, setDraftTopics] = useState(() => normalizeTopics(selectedTopics));
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  const handleStartEdit = () => {
    setDraftTopics(normalizeTopics(selectedTopics));
    setError('');
    setIsEditing(true);
  };

  const handleToggleTopic = (topic) => {
    setDraftTopics((previous) => previous.includes(topic)
      ? previous.filter((item) => item !== topic)
      : [...previous, topic]
    );
  };

  const handleSave = async () => {
    if (draftTopics.length === 0) {
      setError('Select at least one topic.');
      return;
    }
    setSaving(true);
    setError('');
    try {
      await updatePreferences(normalizeTopics(draftTopics));
      setIsEditing(false);
    } catch (err) {
      setError('Failed to save. Please try again.');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="suggestion-panel">
      <div className="suggestion-header-row">
        <div className="suggestion-header">
          <h3><span className="heading-icon">🎯</span> Your Interests</h3>
          <p>{selectedTopics.length ? 'News is filtered using your selected interests.' : 'No interests selected yet.'}</p>
        </div>
        <button className="edit-topics-btn" onClick={handleStartEdit} title="Edit interests">
          <span className="btn-icon">✏️</span> Edit
        </button>
      </div>

      {isEditing ? (
        <>
          <div className="topic-editor-toolbar">
            <button type="button" className="topic-editor-select-all" onClick={() => setDraftTopics(TOPICS)} disabled={saving}>
              Select All
            </button>
            <button type="button" className="topic-editor-remove-all" onClick={() => setDraftTopics([])} disabled={saving}>
              Remove All
            </button>
          </div>
          <div className="topic-editor-grid">
            {TOPICS.map((topic) => (
              <button
                key={topic}
                type="button"
                className={`topic-editor-chip ${draftTopics.includes(topic) ? 'selected' : ''}`}
                onClick={() => handleToggleTopic(topic)}
              >
                <span className="tag-emoji">{getTopicEmoji(topic)}</span>
                <span className="tag-label">{topic}</span>
              </button>
            ))}
          </div>
          {error && <p className="suggestion-error">{error}</p>}
          <div className="topic-editor-actions">
            <button className="topic-editor-save" onClick={handleSave} disabled={saving || draftTopics.length === 0} title={draftTopics.length === 0 ? 'Select at least one topic' : 'Save changes'}>
              <span className="btn-icon">✓</span> {saving ? 'Saving...' : 'Save Changes'}
            </button>
            <button className="topic-editor-cancel" onClick={() => setIsEditing(false)} disabled={saving}>
              <span className="btn-icon">✕</span> Cancel
            </button>
          </div>
        </>
      ) : (
        <>
          <div className="suggestion-tags">
            {selectedTopics.map((topic, index) => (
              <span key={`${topic}-${index}`} className="suggestion-tag">
                <span className="tag-emoji">{getTopicEmoji(topic)}</span>
                <span className="tag-label">{topic}</span>
              </span>
            ))}
          </div>
          <div className="suggestion-message">
            <p>News remains arranged by most recent publication date.</p>
          </div>
        </>
      )}
    </div>
  );
};

export default SuggestionPanel;
