import React from 'react';
import { render, act } from '@testing-library/react';
import { ThemeProvider, useTheme } from './ThemeContext';

let api;
const Probe = () => { api = useTheme(); return null; };
const open = () => render(<ThemeProvider><Probe /></ThemeProvider>);

beforeEach(() => {
  localStorage.clear();
  document.documentElement.removeAttribute('data-theme');
  document.documentElement.className = '';
  delete document.startViewTransition;
});

test('without View Transitions the theme switches at once and is remembered', () => {
  open();
  act(() => api.toggleDarkMode());
  expect(document.documentElement.getAttribute('data-theme')).toBe('dark');
  expect(api.isDarkMode).toBe(true);
  expect(localStorage.getItem('darkMode')).toBe('true');
  act(() => api.toggleDarkMode());
  expect(document.documentElement.hasAttribute('data-theme')).toBe(false);
});

test('with View Transitions the whole page changes in one crossfade', async () => {
  let finish;
  document.startViewTransition = jest.fn((update) => {
    update();
    return { finished: new Promise((resolve) => { finish = resolve; }) };
  });
  open();
  act(() => api.toggleDarkMode());
  expect(document.startViewTransition).toHaveBeenCalledTimes(1);
  expect(document.documentElement.getAttribute('data-theme')).toBe('dark');
  // individual element transitions are paused during the crossfade
  expect(document.documentElement.classList.contains('theme-switching')).toBe(true);
  await act(async () => { finish(); });
  expect(document.documentElement.classList.contains('theme-switching')).toBe(false);
});

test('the saved theme is applied on load', () => {
  localStorage.setItem('darkMode', 'true');
  open();
  expect(document.documentElement.getAttribute('data-theme')).toBe('dark');
});
