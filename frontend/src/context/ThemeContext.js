import React, { createContext, useContext, useState, useEffect, useCallback, useRef } from 'react';
import { flushSync } from 'react-dom';

const ThemeContext = createContext();

const readSaved = () => {
  try {
    const saved = localStorage.getItem('darkMode');
    return saved !== null ? JSON.parse(saved) === true : false;   // default: light
  } catch {
    return false;
  }
};

const applyTheme = (dark) => {
  if (dark) {
    document.documentElement.setAttribute('data-theme', 'dark');
    document.body.setAttribute('data-theme', 'dark');
  } else {
    document.documentElement.removeAttribute('data-theme');
    document.body.removeAttribute('data-theme');
  }
  try { localStorage.setItem('darkMode', JSON.stringify(dark)); } catch { /* private mode */ }
};

const reducedMotion = () =>
  typeof window.matchMedia === 'function' && window.matchMedia('(prefers-reduced-motion: reduce)').matches;

// Light/dark switch. The whole page changes as one: the browser takes a
// snapshot and crossfades it to the new colours in a single short fade
// (View Transitions), instead of every element fading on its own, which is
// slow on long feeds and looks layered. Browsers without View Transitions
// switch instantly.
export const ThemeProvider = ({ children }) => {
  const [isDarkMode, setIsDarkMode] = useState(readSaved);
  const switching = useRef(false);

  useEffect(() => { applyTheme(isDarkMode); }, [isDarkMode]);

  const changeTheme = useCallback((next) => {
    const root = document.documentElement;
    const update = () => {
      // Per-element transitions are paused so nothing fades separately.
      root.classList.add('theme-switching');
      flushSync(() => setIsDarkMode(next));
      applyTheme(next);
    };
    const done = () => {
      root.classList.remove('theme-switching');
      switching.current = false;
    };
    if (switching.current || typeof document.startViewTransition !== 'function' || reducedMotion()) {
      update();
      // Let the browser paint the new colours, then restore normal hover
      // effects (a timer, so it also finishes in a background tab).
      window.setTimeout(done, 100);
      return;
    }
    switching.current = true;
    try {
      document.startViewTransition(update).finished.finally(done);
    } catch {
      update();
      done();
    }
  }, []);

  const toggleDarkMode = useCallback(() => changeTheme(!(document.documentElement.getAttribute('data-theme') === 'dark')),
    [changeTheme]);

  const value = {
    isDarkMode,
    toggleDarkMode,
    setIsDarkMode: changeTheme,
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
