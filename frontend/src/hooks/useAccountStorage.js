import { useState, useEffect, useCallback } from 'react';
import { useAuth } from '../context/AuthContext';

// State includes its owner so account switches cannot write the previous user's data.
export const useAccountStorage = (prefix, fallback) => {
  const {user} = useAuth();
  const key = user?.email ? `${prefix}:${user.email.toLowerCase()}` : null;
  const read = useCallback(() => {
    try { const value = key && JSON.parse(localStorage.getItem(key)); return Array.isArray(value) ? value : fallback; }
    catch { return fallback; }
  }, [key, fallback]);
  const [state, setState] = useState(() => ({key, value:read()}));
  const value = state.key === key ? state.value : read();
  useEffect(() => {
    const sync = event => { if (event.key === key) setState({key,value:read()}); };
    window.addEventListener('storage', sync);
    return () => window.removeEventListener('storage', sync);
  }, [key, read]);
  const update = useCallback(next => {
    if (!key) return;
    // Read current browser value, avoiding side effects inside a React state updater.
    const result = typeof next === 'function' ? next(read()) : next;
    localStorage.setItem(key, JSON.stringify(result));
    setState({key, value:result});
  }, [key, read]);
  return [value, update];
};
