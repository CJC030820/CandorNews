import React, { useEffect, useRef, useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { useNavigate, Link } from 'react-router-dom';
import PageWrapper from '../components/PageWrapper';
import { markGuidePending } from '../utils/firstTimeGuide';
import './RegisterPage.css';

const SUCCESS_DELAY_MS = 1500;

const RegisterPage = () => {
  const [formData, setFormData] = useState({
    name: '',
    email: '',
    password: '',
    confirmPassword: '',
  });
  const [error, setError] = useState('');
  // Email of an account that already exists, shown as a warning with a login link.
  const [existingEmail, setExistingEmail] = useState('');
  const [loading, setLoading] = useState(false);
  // After a successful registration: show a success message, then open the login page.
  const [registered, setRegistered] = useState(false);
  const redirectTimer = useRef(null);
  useEffect(() => () => clearTimeout(redirectTimer.current), []);
  const { register } = useAuth();
  const navigate = useNavigate();

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
    if (name === 'email') setExistingEmail('');
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setExistingEmail('');

    if (formData.password !== formData.confirmPassword) {
      setError('Passwords do not match');
      return;
    }

    if (formData.password.length < 8) {
      setError('Password must be at least 8 characters');
      return;
    }

    setLoading(true);
    try {
      const success = await register(formData.name, formData.email, formData.password);
      if (success) {
        const email = formData.email.trim();
        // Show the first-time guide after this account's first login.
        markGuidePending(email);
        setRegistered(true);
        redirectTimer.current = setTimeout(() => navigate('/login', { state: { email, registered: true } }), SUCCESS_DELAY_MS);
      } else {
        setError('Registration failed. Email may already exist.');
      }
    } catch (err) {
      const status = err.response?.status;
      const detail = String(err.response?.data?.detail || '');
      if (status === 400 && /already registered/i.test(detail)) {
        setExistingEmail(formData.email.trim());
      } else if (status === 422) {
        setError('Please check your details: enter your name, a valid email address and a password of 8 to 72 characters.');
      } else if (!err.response) {
        setError('Could not reach the server. Please check your connection and try again.');
      } else {
        setError('Registration failed. Please try again.');
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <PageWrapper>
    <div className="register-container">
      <div className="register-box">
        <div className="register-header">
          <h1>CandorNews</h1>
          <p>Create Your Account</p>
        </div>

        <form onSubmit={handleSubmit} className="register-form">
          <div className="form-group">
            <label htmlFor="name">Full Name</label>
            <input
              id="name"
              type="text"
              name="name"
              value={formData.name}
              onChange={handleChange}
              placeholder="Enter your full name"
              required
              disabled={loading}
            />
          </div>

          <div className="form-group">
            <label htmlFor="email">Email Address</label>
            <input
              id="email"
              type="email"
              name="email"
              value={formData.email}
              onChange={handleChange}
              placeholder="Enter your email"
              required
              disabled={loading}
            />
          </div>

          <div className="form-group">
            <label htmlFor="password">Password</label>
            <input
              id="password"
              type="password"
              name="password"
              value={formData.password}
              onChange={handleChange}
              placeholder="At least 6 characters"
              required
              disabled={loading}
            />
          </div>

          <div className="form-group">
            <label htmlFor="confirmPassword">Confirm Password</label>
            <input
              id="confirmPassword"
              type="password"
              name="confirmPassword"
              value={formData.confirmPassword}
              onChange={handleChange}
              placeholder="Confirm your password"
              required
              disabled={loading}
            />
          </div>

          {registered && (
            <div className="register-success" role="status">
              <strong>Registration successful!</strong> Taking you to the login page...
            </div>
          )}
          {existingEmail && (
            <div className="register-warning" role="alert">
              <strong>This email is already registered.</strong>{' '}
              An account with <span className="register-warning-email">{existingEmail}</span> already exists.{' '}
              <Link to="/login" state={{ email: existingEmail }}>Log in instead</Link>
            </div>
          )}
          {error && <div className="error-message" role="alert">{error}</div>}

          <button type="submit" disabled={loading || registered} className="register-button">
            {loading ? 'Creating Account...' : 'Register'}
          </button>
        </form>

        <div className="register-footer">
          <p>Already have an account? <Link to="/login">Login here</Link></p>
        </div>
      </div>
    </div>
    </PageWrapper>
  );
};

export default RegisterPage;
