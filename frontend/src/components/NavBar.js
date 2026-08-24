import React from 'react';
import { useAuth } from '../context/AuthContext';
import { useNavigate } from 'react-router-dom';
import DarkModeToggle from '../components/DarkModeToggle';
import './NavBar.css';

const NavBar = ({ searchQuery, onSearchChange }) => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <nav className="navbar">
      <div className="navbar-content">
        <div className="logo">
          <button
            className="logo-button"
            onClick={() => navigate('/feed')}
            title="Go to main page"
            aria-label="CandorNews - Go to main page"
          >
            <h2>CandorNews</h2>
          </button>
        </div>

        <div className="search-bar-container">
          <div className="search-bar">
            <span className="search-icon">🔍</span>
            <input
              type="text"
              placeholder="Search articles..."
              value={searchQuery}
              onChange={(e) => onSearchChange(e.target.value)}
              className="search-input"
            />
            {searchQuery && (
              <button
                onClick={() => onSearchChange('')}
                className="search-clear"
                title="Clear search"
              >
                ✕
              </button>
            )}
          </div>
        </div>

        <div className="navbar-actions">
          {user && (
            <>
              <a href="/bookmarks" className="nav-button">
                📑 Bookmarks
              </a>
              <a href="/history" className="nav-button">
                🕘 History
              </a>
              <a href="/profile" className="nav-button">
                👤 Profile
              </a>
              <DarkModeToggle />
              <button onClick={handleLogout} className="nav-button logout" title="Logout">
                ⏻
              </button>
            </>
          )}
        </div>
      </div>
    </nav>
  );
};

export default NavBar;