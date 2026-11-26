import React, { useEffect, useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import PageWrapper from '../components/PageWrapper';
import './LoginPage.css';

const RESEND_SECONDS = 60;

// Forgot password: (1) enter the account email and receive a 6-digit code,
// (2) enter the code and a new password. The server replies the same way
// whether or not the email has an account, so this page cannot reveal who is registered.
const ForgotPasswordPage = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const { requestPasswordReset, confirmPasswordReset } = useAuth();
  const [step, setStep] = useState('email');
  const [email, setEmail] = useState(location.state?.email || '');
  const [code, setCode] = useState('');
  const [password, setPassword] = useState('');
  const [confirm, setConfirm] = useState('');
  const [info, setInfo] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [wait, setWait] = useState(0);

  useEffect(() => {
    if (!wait) return undefined;
    const timer = setTimeout(() => setWait((w) => w - 1), 1000);
    return () => clearTimeout(timer);
  }, [wait]);

  const sendCode = async (e) => {
    e?.preventDefault();
    setError(''); setLoading(true);
    try {
      const data = await requestPasswordReset(email.trim());
      setInfo(data.detail);
      setStep('code');
      setWait(RESEND_SECONDS);
    } catch (err) {
      setError(err.response?.status === 422 ? 'Please enter a valid email address.'
        : !err.response ? 'Could not reach the server. Please check your connection and try again.'
          : 'Could not send the code. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const resetPassword = async (e) => {
    e.preventDefault();
    setError('');
    if (!/^\d{6}$/.test(code.trim())) { setError('Enter the 6-digit code from the email.'); return; }
    if (password.length < 8) { setError('Password must be at least 8 characters.'); return; }
    if (password !== confirm) { setError('Passwords do not match.'); return; }
    setLoading(true);
    try {
      await confirmPasswordReset(email.trim(), code.trim(), password);
      navigate('/login', { replace: true, state: { email: email.trim(), passwordReset: true } });
    } catch (err) {
      setError(err.response?.data?.detail && typeof err.response.data.detail === 'string'
        ? err.response.data.detail
        : err.response?.status === 422 ? 'Please check the code and use a password of 8 to 72 characters.'
          : !err.response ? 'Could not reach the server. Please check your connection and try again.'
            : 'Could not reset the password. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <PageWrapper>
      <div className="login-container">
        <div className="login-box">
          <div className="login-header">
            <h1>CandorNews</h1>
            <p>Reset your password</p>
          </div>

          {step === 'email' ? (
            <form onSubmit={sendCode} className="login-form">
              <p className="login-hint">
                Enter the email address of your account. We will email you a 6-digit code to choose a new password.
              </p>
              <div className="form-group">
                <label htmlFor="reset-email">Email Address</label>
                <input id="reset-email" type="email" value={email} onChange={(e) => setEmail(e.target.value)}
                  placeholder="Enter your email" required disabled={loading} autoComplete="email" />
              </div>
              {error && <div className="error-message" role="alert">{error}</div>}
              <button type="submit" disabled={loading} className="login-button">
                {loading ? 'Sending code...' : 'Send code'}
              </button>
            </form>
          ) : (
            <form onSubmit={resetPassword} className="login-form">
              <div className="login-success" role="status">{info}</div>
              <p className="login-hint">Code sent to <strong>{email}</strong>. Check your spam folder if it does not arrive.</p>
              <div className="form-group">
                <label htmlFor="reset-code">6-digit code</label>
                <input id="reset-code" inputMode="numeric" autoComplete="one-time-code" maxLength={6}
                  value={code} onChange={(e) => setCode(e.target.value.replace(/\D/g, ''))}
                  placeholder="Enter the code" required disabled={loading} />
              </div>
              <div className="form-group">
                <label htmlFor="reset-password">New password</label>
                <input id="reset-password" type="password" value={password} onChange={(e) => setPassword(e.target.value)}
                  placeholder="At least 8 characters" required disabled={loading} autoComplete="new-password" />
              </div>
              <div className="form-group">
                <label htmlFor="reset-confirm">Confirm new password</label>
                <input id="reset-confirm" type="password" value={confirm} onChange={(e) => setConfirm(e.target.value)}
                  placeholder="Confirm your new password" required disabled={loading} autoComplete="new-password" />
              </div>
              {error && <div className="error-message" role="alert">{error}</div>}
              <button type="submit" disabled={loading} className="login-button">
                {loading ? 'Saving...' : 'Change password'}
              </button>
              <div className="login-hint login-hint-actions">
                <button type="button" className="link-button" onClick={sendCode} disabled={loading || wait > 0}>
                  {wait > 0 ? `Send a new code in ${wait}s` : 'Send a new code'}
                </button>
                <button type="button" className="link-button"
                  onClick={() => { setStep('email'); setCode(''); setError(''); }} disabled={loading}>
                  Use a different email
                </button>
              </div>
            </form>
          )}

          <div className="login-footer">
            <p>Remembered it? <Link to="/login" state={{ email }}>Back to login</Link></p>
          </div>
        </div>
      </div>
    </PageWrapper>
  );
};

export default ForgotPasswordPage;
