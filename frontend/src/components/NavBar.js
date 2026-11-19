import React from 'react';
import { useAuth } from '../context/AuthContext';
import { useNavigate, Link } from 'react-router-dom';
import DarkModeToggle from '../components/DarkModeToggle';
import SearchBox from './SearchBox';
import './NavBar.css';
import { BookmarkIcon, HistoryIcon, HelpIcon, UserIcon } from './Icons';

const NavBar = ({ searchQuery, onSearchChange }) => {
  const { user } = useAuth();
  const navigate = useNavigate();

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
            <span className="logo-brand">
              <img src="/CandorNews-removebg-preview.png" alt="" className="logo-image" />
              <h2>CandorNews</h2>
            </span>
          </button>
        </div>

        <SearchBox value={searchQuery} onChange={onSearchChange} />

        <div className="navbar-actions">
          {user && (
            <>
              <Link to="/bookmarks" className="nav-button" aria-label="Bookmarks" title="Bookmarks">
                <span className="nav-icon" aria-hidden="true"><BookmarkIcon /></span>
                <span className="nav-label">Bookmarks</span>
              </Link>
              <Link to="/history" className="nav-button" aria-label="History" title="History">
                <span className="nav-icon" aria-hidden="true"><HistoryIcon /></span>
                <span className="nav-label">History</span>
              </Link>
              <Link to="/help" className="nav-button" aria-label="Help" title="Help">
                <span className="nav-icon" aria-hidden="true"><HelpIcon /></span>
                <span className="nav-label">Help</span>
              </Link>
              <Link to="/profile" className="nav-button" aria-label="Profile" title="Profile">
                <span className="nav-icon" aria-hidden="true"><UserIcon /></span>
                <span className="nav-label">Profile</span>
              </Link>
              <DarkModeToggle />
            </>
          )}
        </div>
      </div>
    </nav>
  );
};

export default NavBar;
