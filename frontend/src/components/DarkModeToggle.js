import React, { useEffect, useState } from 'react';
import { useTheme } from '../context/ThemeContext';
import './DarkModeToggle.css';

const DarkModeToggle = () => {
  const { isDarkMode, toggleDarkMode } = useTheme();
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  const handleClick = (e) => {
    e.preventDefault();
    e.stopPropagation();
    console.log('Button clicked, current isDarkMode:', isDarkMode);
    toggleDarkMode();
  };

  if (!mounted) {
    return null;
  }

  return (
    <button
      className="dark-mode-toggle"
      onClick={handleClick}
      title={isDarkMode ? 'Switch to light mode' : 'Switch to dark mode'}
      aria-label="Toggle dark mode"
      type="button"
    >
      <span className="theme-icon">
        {isDarkMode ? '☀️' : '🌙'}
      </span>
    </button>
  );
};

export default DarkModeToggle;
