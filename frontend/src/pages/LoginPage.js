import React, { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { useNavigate, Link, useLocation } from 'react-router-dom';
import PageWrapper from '../components/PageWrapper';
import './LoginPage.css';

const LoginPage = () => {
  const location = useLocation();
  // Filled in when the user came from "Log in instead" on the register page.
  const [email, setEmail] = useState(location.state?.email || '');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    try {
      const success = await login(email, password);
      if (success) {
        let returnPath = null;
        try {
          returnPath = sessionStorage.getItem('returnAfterLogin');
          sessionStorage.removeItem('returnAfterLogin');
        } catch { /* storage unavailable */ }
        // replace: the login page should not stay in the history, so the
        // browser's back button does not return to it.
        navigate(returnPath && returnPath.startsWith('/article/') ? returnPath : '/feed', { replace: true });
      } else {
        setError('Invalid email or password');
      }
    } catch (err) {
      setError('Login failed. Please try again.');
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
          <p>Trusted Malaysia English News</p>
        </div>
        
        <form onSubmit={handleSubmit} className="login-form">
          {location.state?.registered && !error && (
            <div className="login-success" role="status">
              Your account has been created. Log in with your new password.
            </div>
          )}
          <div className="form-group">
            <label htmlFor="email">Email Address</label>
            <input
              id="email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
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
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Enter your password"
              required
              disabled={loading}
            />
          </div>

          {error && <div className="error-message">{error}</div>}

          <button type="submit" disabled={loading} className="login-button">
            {loading ? 'Logging in...' : 'Login'}
          </button>
        </form>

        <div className="login-footer">
          <p>Don't have an account? <Link to="/register">Register here</Link></p>
        </div>
      </div>
    </div>
    </PageWrapper>
  );
};

export default LoginPage;
