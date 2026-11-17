import React, { createContext, useContext, useState, useEffect, useRef } from 'react';

const ThemeContext = createContext();

export const ThemeProvider = ({ children }) => {
  const initialThemeApplied = useRef(false);
  const transitionTimer = useRef(null);
  const [isDarkMode, setIsDarkMode] = useState(() => {
    // Check localStorage for saved preference
    const saved = localStorage.getItem('darkMode');
    if (saved !== null) {
      try {
        return JSON.parse(saved);
      } catch (e) {
        console.error('Error parsing theme from localStorage:', e);
        return false; // Default to light mode
      }
    }
    // Default to light mode (false = light, true = dark)
    return false;
  });

  // Apply theme on mount and when isDarkMode changes
  useEffect(() => {
    const root = document.documentElement;
    const animateThemeChange = initialThemeApplied.current;
    if (transitionTimer.current) {
      window.clearTimeout(transitionTimer.current);
      transitionTimer.current = null;
    }
    if (animateThemeChange) {
      root.classList.add('theme-color-transition');
    }
    initialThemeApplied.current = true;

    // Save preference in the browser and apply both theme attributes together.
    localStorage.setItem('darkMode', JSON.stringify(isDarkMode));
    if (isDarkMode) {
      document.documentElement.setAttribute('data-theme', 'dark');
      document.body.setAttribute('data-theme', 'dark');
    } else {
      document.documentElement.removeAttribute('data-theme');
      document.body.removeAttribute('data-theme');
    }
    
    if (animateThemeChange) {
      transitionTimer.current = window.setTimeout(() => {
        root.classList.remove('theme-color-transition');
        transitionTimer.current = null;
      }, 1100);
    }

    console.log('Theme updated:', isDarkMode ? 'dark' : 'light');
    return () => {
      if (transitionTimer.current) {
        window.clearTimeout(transitionTimer.current);
        transitionTimer.current = null;
      }
    };
  }, [isDarkMode]);

  const toggleDarkMode = () => {
    console.log('Toggle dark mode clicked');
    setIsDarkMode(prev => {
      console.log('Toggling from:', prev, 'to:', !prev);
      return !prev;
    });
  };

  const value = {
    isDarkMode,
    toggleDarkMode,
    setIsDarkMode // Allow direct setting if needed
  };

  return (
    <ThemeContext.Provider value={value}>
      {children}
    </ThemeContext.Provider>
  );
};

export const useTheme = () => {
  const context = useContext(ThemeContext);
  if (!context) {
    throw new Error('useTheme must be used within ThemeProvider');
  }
  return context;
};
