import React, { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { useBookmarks } from '../context/BookmarkContext';
import { useReadArticles } from '../context/ReadArticlesContext';
import { useNavigate } from 'react-router-dom';
import BackToTopButton from '../components/BackToTopButton';
import './ProfilePage.css';

const ProfilePage = () => {
  const {
    user,
    logout,
    updateProfile,
    getEmailStatus,
    updateEmailSettings,
    sendEmailTest,
    deleteAccount,
    selectedTopics
  } = useAuth();
  const { bookmarks } = useBookmarks();
  const { readCount } = useReadArticles();
  const navigate = useNavigate();

  const [isEditingName, setIsEditingName] = useState(false);
  const [nameInput, setNameInput] = useState(user?.name || '');
  const [savingName, setSavingName] = useState(false);
  const [nameError, setNameError] = useState('');

  const [emailEnabled, setEmailEnabled] = useState(user?.email_notifications_enabled || false);
  const [emailSchedule, setEmailSchedule] = useState(user?.email_notification_schedule || 'morning');
  const [emailServerConfigured, setEmailServerConfigured] = useState(true);
  const [togglingEmail, setTogglingEmail] = useState(false);
  const [savingSchedule, setSavingSchedule] = useState(false);
  const [sendingEmailNow, setSendingEmailNow] = useState(false);
  const [emailStatusMessage, setEmailStatusMessage] = useState(null);

  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [deletePassword, setDeletePassword] = useState('');
  const [deletingAccount, setDeletingAccount] = useState(false);
  const [deleteError, setDeleteError] = useState('');

  useEffect(() => {
    if (user?.name !== undefined) {
      setNameInput(user.name);
    }
  }, [user?.name]);

  useEffect(() => {
    const loadEmailStatus = async () => {
      try {
        const status = await getEmailStatus();
        setEmailEnabled(status.email_notifications_enabled || false);
        setEmailSchedule(status.email_notification_schedule || 'morning');
        setEmailServerConfigured(status.server_configured);
      } catch (err) {
        // Non-fatal; keep whatever came from the user object
      }
    };
    loadEmailStatus();
  }, []);

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const handleStartEditName = () => {
    setNameInput(user?.name || '');
    setNameError('');
    setIsEditingName(true);
  };

  const handleCancelEditName = () => {
    setNameInput(user?.name || '');
    setNameError('');
    setIsEditingName(false);
  };

  const handleSaveName = async () => {
    const trimmed = nameInput.trim();
    if (!trimmed) {
      setNameError('Name cannot be empty.');
      return;
    }
    setNameError('');
    setSavingName(true);
    try {
      await updateProfile(trimmed);
      setIsEditingName(false);
    } catch (err) {
      const detail = err?.response?.data?.detail || 'Failed to update name.';
      setNameError(detail);
    } finally {
      setSavingName(false);
    }
  };

  const handleNameKeyDown = (e) => {
    if (e.key === 'Enter') {
      handleSaveName();
    } else if (e.key === 'Escape') {
      handleCancelEditName();
    }
  };

  const handleToggleEmailNotifications = async () => {
    const newValue = !emailEnabled;
    setEmailStatusMessage(null);
    setTogglingEmail(true);
    try {
      const updated = await updateEmailSettings({ emailNotificationsEnabled: newValue });
      setEmailEnabled(updated.email_notifications_enabled);
    } catch (err) {
      const detail = err?.response?.data?.detail || 'Failed to update email notification setting.';
      setEmailStatusMessage({ type: 'error', text: detail });
    } finally {
      setTogglingEmail(false);
    }
  };

  const handleChangeSchedule = async (schedule) => {
    if (schedule === emailSchedule) return;
    setEmailStatusMessage(null);
    setSavingSchedule(true);
    try {
      const updated = await updateEmailSettings({ emailNotificationSchedule: schedule });
      setEmailSchedule(updated.email_notification_schedule);
    } catch (err) {
      const detail = err?.response?.data?.detail || 'Failed to update schedule.';
      setEmailStatusMessage({ type: 'error', text: detail });
    } finally {
      setSavingSchedule(false);
    }
  };

  const handleSendEmailNow = async () => {
    setEmailStatusMessage(null);
    setSendingEmailNow(true);
    try {
      await sendEmailTest();
      setEmailStatusMessage({ type: 'success', text: '✅ Notification email sent! Check your inbox.' });
    } catch (err) {
      const detail = err?.response?.data?.detail || 'Failed to send notification email.';
      setEmailStatusMessage({ type: 'error', text: detail });
    } finally {
      setSendingEmailNow(false);
    }
  };

  const handleOpenDeleteModal = () => {
    setDeletePassword('');
    setDeleteError('');
    setShowDeleteModal(true);
  };

  const handleCloseDeleteModal = () => {
    if (deletingAccount) return;
    setShowDeleteModal(false);
    setDeletePassword('');
    setDeleteError('');
  };

  const handleConfirmDeleteAccount = async () => {
    if (!deletePassword) {
      setDeleteError('Please enter your password to confirm.');
      return;
    }
    setDeleteError('');
    setDeletingAccount(true);
    try {
      await deleteAccount(deletePassword);
      navigate('/login');
    } catch (err) {
      const detail = err?.response?.data?.detail || 'Failed to delete account. Please try again.';
      setDeleteError(detail);
    } finally {
      setDeletingAccount(false);
    }
  };

  return (
    <div className="profile-page">
      <BackToTopButton />
      <div className="profile-page-wrapper">
        <button className="back-btn" onClick={() => navigate('/feed')}>
          <span className="back-btn-icon">←</span>
          <span className="back-btn-label">Back to Main Page</span>
        </button>

        <div className="profile-container">
          <div className="profile-card">
            <div className="profile-avatar">👤</div>
            <div className="profile-info">
              {isEditingName ? (
                <div className="name-edit-group">
                  <input
                    type="text"
                    className="name-edit-input"
                    value={nameInput}
                    onChange={(e) => setNameInput(e.target.value)}
                    onKeyDown={handleNameKeyDown}
                    disabled={savingName}
                    autoFocus
                    maxLength={50}
                  />
                  <div className="name-edit-actions">
                    <button
                      className="name-save-btn"
                      onClick={handleSaveName}
                      disabled={savingName || !nameInput.trim()}
                    >
                      {savingName ? 'Saving...' : '✓ Save'}
                    </button>
                    <button
                      className="name-cancel-btn"
                      onClick={handleCancelEditName}
                      disabled={savingName}
                    >
                      ✕ Cancel
                    </button>
                  </div>
                  {nameError && <p className="name-error">{nameError}</p>}
                </div>
              ) : (
                <h1 className="profile-name">
                  {user?.name || 'User'}
                  <button
                    className="edit-name-btn"
                    onClick={handleStartEditName}
                    title="Edit name"
                    aria-label="Edit name"
                  >
                    ✏️
                  </button>
                </h1>
              )}
              <p>{user?.email || 'user@example.com'}</p>
            </div>
          </div>

          <div className="profile-stats">
            <div
              className="stat stat-clickable"
              onClick={() => navigate('/history')}
              onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') navigate('/history'); }}
              role="button"
              tabIndex={0}
              title="View your reading history"
            >
              <span className="stat-number">{readCount}</span>
              <span className="stat-label">Articles Read</span>
            </div>
            <div
              className="stat stat-clickable"
              onClick={() => navigate('/bookmarks')}
              onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') navigate('/bookmarks'); }}
              role="button"
              tabIndex={0}
              title="View your bookmarks"
            >
              <span className="stat-number">{bookmarks.length}</span>
              <span className="stat-label">Bookmarks</span>
            </div>
            <div
              className="stat stat-clickable"
              onClick={() => navigate('/feed')}
              onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') navigate('/feed'); }}
              role="button"
              tabIndex={0}
              title="Go to main page"
            >
              <span className="stat-number">{selectedTopics.length}</span>
              <span className="stat-label">Topics</span>
            </div>
          </div>

          <div className="profile-section">
            <h2>✉️ Email Notifications</h2>

            {!emailServerConfigured && (
              <div className="email-warning">
                ⚠️ Email sending isn't configured on the server yet (demo mode).
                You can still save your preferences and preview the flow — sending will
                return a friendly error until SMTP credentials are set.
              </div>
            )}

            <div className="preference-item">
              <label>Enable Email Notifications</label>
              <input
                type="checkbox"
                checked={emailEnabled}
                disabled={togglingEmail}
                onChange={handleToggleEmailNotifications}
              />
            </div>

            <div className="email-schedule-row">
              <label>Delivery Time</label>
              <div className="email-schedule-options">
                <button
                  type="button"
                  className={`schedule-option ${emailSchedule === 'morning' ? 'selected' : ''}`}
                  onClick={() => handleChangeSchedule('morning')}
                  disabled={savingSchedule}
                >
                  ☀️ Morning
                  <span className="schedule-time">7:00 AM</span>
                </button>
                <button
                  type="button"
                  className={`schedule-option ${emailSchedule === 'night' ? 'selected' : ''}`}
                  onClick={() => handleChangeSchedule('night')}
                  disabled={savingSchedule}
                >
                  🌙 Night
                  <span className="schedule-time">7:00 PM</span>
                </button>
                <button
                  type="button"
                  className={`schedule-option ${emailSchedule === 'both' ? 'selected' : ''}`}
                  onClick={() => handleChangeSchedule('both')}
                  disabled={savingSchedule}
                >
                  🔄 Day &amp; Night
                  <span className="schedule-time">7 AM &amp; 7 PM</span>
                </button>
              </div>
            </div>

            <button
              className="email-test-btn"
              onClick={handleSendEmailNow}
              disabled={sendingEmailNow}
            >
              {sendingEmailNow ? 'Sending...' : '📨 Send Notification Now'}
            </button>

            {emailStatusMessage && (
              <div className={`email-status ${emailStatusMessage.type}`}>
                {emailStatusMessage.text}
              </div>
            )}
          </div>

          <button className="logout-button" onClick={handleLogout}>Logout</button>

          <div className="danger-zone">
            <h2>⚠️ Danger Zone</h2>
            <p className="danger-zone-desc">
              Deleting your account is permanent and cannot be undone. All your
              profile data will be removed immediately.
            </p>
            <button className="delete-account-btn" onClick={handleOpenDeleteModal}>
              🗑️ Delete Account
            </button>
          </div>
        </div>
      </div>

      {showDeleteModal && (
        <div className="delete-modal-overlay" onClick={handleCloseDeleteModal}>
          <div className="delete-modal" onClick={(e) => e.stopPropagation()}>
            <h3>🗑️ Delete Account</h3>
            <p>
              This will <strong>permanently delete</strong> your account
              (<strong>{user?.email}</strong>) and cannot be undone. Enter your
              password to confirm.
            </p>
            <input
              type="password"
              className="delete-password-input"
              placeholder="Enter your password"
              value={deletePassword}
              onChange={(e) => setDeletePassword(e.target.value)}
              disabled={deletingAccount}
              autoFocus
            />
            {deleteError && <p className="delete-error">{deleteError}</p>}
            <div className="delete-modal-actions">
              <button
                className="delete-cancel-btn"
                onClick={handleCloseDeleteModal}
                disabled={deletingAccount}
              >
                Cancel
              </button>
              <button
                className="delete-confirm-btn"
                onClick={handleConfirmDeleteAccount}
                disabled={deletingAccount || !deletePassword}
              >
                {deletingAccount ? 'Deleting...' : 'Permanently Delete'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default ProfilePage;
