import React, { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { useBookmarks } from '../context/BookmarkContext';
import { useReadArticles } from '../context/ReadArticlesContext';
import { useNavigate } from 'react-router-dom';
import PageWrapper from '../components/PageWrapper';
import BackToTopButton from '../components/BackToTopButton';
import './ProfilePage.css';

export const MAX_NOTIFICATION_TIMES = 3;

// "19:30" -> "7:30 PM"
export const formatTime = (value) => {
  const [hour, minute] = value.split(':').map(Number);
  if (Number.isNaN(hour) || Number.isNaN(minute)) return value;
  const suffix = hour < 12 ? 'AM' : 'PM';
  return `${hour % 12 || 12}:${String(minute).padStart(2, '0')} ${suffix}`;
};

const ProfilePage = () => {
  const {
    user,
    logout,
    updateProfile,
    getEmailStatus,
    updateEmailSettings,
    sendEmailTest,
    requestEmailVerification,
    confirmEmailVerification,
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
  const [savedTimes, setSavedTimes] = useState(user?.email_notification_times || ['07:00']);
  const [draftTimes, setDraftTimes] = useState(user?.email_notification_times || ['07:00']);
  const [maxTimes, setMaxTimes] = useState(MAX_NOTIFICATION_TIMES);
  const [emailServerConfigured, setEmailServerConfigured] = useState(true);
  const [emailVerified, setEmailVerified] = useState(Boolean(user?.email_verified));
  const [verificationCode, setVerificationCode] = useState('');
  const [codeSent, setCodeSent] = useState(false);
  const [verifying, setVerifying] = useState(false);
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
        const times = status.email_notification_times?.length ? status.email_notification_times : ['07:00'];
        setSavedTimes(times);
        setDraftTimes(times);
        setMaxTimes(status.max_notification_times || MAX_NOTIFICATION_TIMES);
        setEmailServerConfigured(status.server_configured);
        setEmailVerified(Boolean(status.email_verified));
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

  const timesChanged = [...draftTimes].sort().join(',') !== [...savedTimes].sort().join(',');

  const handleTimeChange = (index, value) => {
    setEmailStatusMessage(null);
    setDraftTimes((times) => times.map((time, i) => (i === index ? value : time)));
  };

  const handleAddTime = () => {
    if (draftTimes.length >= maxTimes) return;
    const suggestion = ['12:00', '19:00', '07:00', '21:00'].find((t) => !draftTimes.includes(t)) || '12:00';
    setEmailStatusMessage(null);
    setDraftTimes((times) => [...times, suggestion]);
  };

  const handleRemoveTime = (index) => {
    if (draftTimes.length <= 1) return;
    setEmailStatusMessage(null);
    setDraftTimes((times) => times.filter((_, i) => i !== index));
  };

  const handleSaveTimes = async () => {
    if (draftTimes.some((time) => !time)) {
      setEmailStatusMessage({ type: 'error', text: 'Please fill in every delivery time.' });
      return;
    }
    if (new Set(draftTimes).size !== draftTimes.length) {
      setEmailStatusMessage({ type: 'error', text: 'Each delivery time must be different.' });
      return;
    }
    setEmailStatusMessage(null);
    setSavingSchedule(true);
    try {
      const updated = await updateEmailSettings({ emailNotificationTimes: draftTimes });
      const times = updated.email_notification_times?.length ? updated.email_notification_times : draftTimes;
      setSavedTimes(times);
      setDraftTimes(times);
      setEmailStatusMessage({ type: 'success', text: `Delivery times saved: ${times.map(formatTime).join(', ')} (Malaysia time).` });
    } catch (err) {
      const detail = err?.response?.data?.detail;
      setEmailStatusMessage({ type: 'error', text: typeof detail === 'string' ? detail : 'Failed to save delivery times.' });
    } finally {
      setSavingSchedule(false);
    }
  };

  const errorText = (err, fallback) => {
    const detail = err?.response?.data?.detail;
    return typeof detail === 'string' ? detail : fallback;
  };

  const handleSendCode = async () => {
    setEmailStatusMessage(null);
    setVerifying(true);
    try {
      await requestEmailVerification();
      setCodeSent(true);
      setEmailStatusMessage({ type: 'success', text: `A 6-digit code was sent to ${user?.email}. It expires in 15 minutes.` });
    } catch (err) {
      setEmailStatusMessage({ type: 'error', text: errorText(err, 'Could not send the code. Please try again.') });
    } finally {
      setVerifying(false);
    }
  };

  const handleConfirmCode = async () => {
    setEmailStatusMessage(null);
    setVerifying(true);
    try {
      const updated = await confirmEmailVerification(verificationCode.trim());
      setEmailVerified(Boolean(updated.email_verified));
      setVerificationCode('');
      setEmailStatusMessage({ type: 'success', text: '✅ Email verified. You will now receive digests at your delivery times.' });
    } catch (err) {
      setEmailStatusMessage({ type: 'error', text: errorText(err, 'Verification failed. Please try again.') });
    } finally {
      setVerifying(false);
    }
  };

  const handleSendEmailNow = async () => {
    setEmailStatusMessage(null);
    setSendingEmailNow(true);
    try {
      await sendEmailTest();
      setEmailStatusMessage({ type: 'success', text: '✅ Notification email sent! Check your inbox.' });
    } catch (err) {
      setEmailStatusMessage({ type: 'error', text: errorText(err, 'Failed to send notification email.') });
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
    <PageWrapper>
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

            {!emailVerified && (
              <div className="email-verify-box">
                <p className="email-verify-title">Verify your email address</p>
                <p className="email-verify-text">
                  Digests are only sent after you confirm that you own <strong>{user?.email}</strong>.
                </p>
                <div className="email-verify-row">
                  <button type="button" className="email-verify-send" onClick={handleSendCode} disabled={verifying}>
                    {codeSent ? 'Send a new code' : 'Send verification code'}
                  </button>
                  {codeSent && (
                    <>
                      <input
                        type="text"
                        inputMode="numeric"
                        autoComplete="one-time-code"
                        maxLength={6}
                        className="email-verify-input"
                        placeholder="6-digit code"
                        aria-label="Verification code"
                        value={verificationCode}
                        onChange={(e) => setVerificationCode(e.target.value.replace(/\D/g, ''))}
                        disabled={verifying}
                      />
                      <button
                        type="button"
                        className="email-verify-confirm"
                        onClick={handleConfirmCode}
                        disabled={verifying || verificationCode.length !== 6}
                      >
                        Verify
                      </button>
                    </>
                  )}
                </div>
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
              <label>Delivery Times <span className="schedule-hint">(Malaysia time, GMT+8 · up to {maxTimes})</span></label>
              <div className="email-time-list">
                {draftTimes.map((time, index) => (
                  <div className="email-time-item" key={index}>
                    <input
                      type="time"
                      className="email-time-input"
                      value={time}
                      onChange={(e) => handleTimeChange(index, e.target.value)}
                      disabled={savingSchedule}
                      aria-label={`Delivery time ${index + 1}`}
                    />
                    <span className="schedule-time">{time ? formatTime(time) : ''}</span>
                    <button
                      type="button"
                      className="email-time-remove"
                      onClick={() => handleRemoveTime(index)}
                      disabled={savingSchedule || draftTimes.length <= 1}
                      aria-label={`Remove delivery time ${index + 1}`}
                      title={draftTimes.length <= 1 ? 'At least one time is required' : 'Remove this time'}
                    >
                      ✕
                    </button>
                  </div>
                ))}
              </div>
              <div className="email-time-actions">
                <button
                  type="button"
                  className="email-time-add"
                  onClick={handleAddTime}
                  disabled={savingSchedule || draftTimes.length >= maxTimes}
                >
                  ＋ Add time{draftTimes.length >= maxTimes ? ` (maximum ${maxTimes})` : ''}
                </button>
                <button
                  type="button"
                  className="email-time-save"
                  onClick={handleSaveTimes}
                  disabled={savingSchedule || !timesChanged}
                >
                  {savingSchedule ? 'Saving...' : 'Save times'}
                </button>
              </div>
            </div>

            <button
              className="email-test-btn"
              onClick={handleSendEmailNow}
              disabled={sendingEmailNow || !emailVerified}
              title={emailVerified ? 'Send a digest to your email now' : 'Verify your email address first'}
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
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !deletingAccount && deletePassword) {
                  handleConfirmDeleteAccount();
                }
              }}
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
    </PageWrapper>
  );
};

export default ProfilePage;
