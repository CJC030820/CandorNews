import { useEffect, useRef, useCallback } from 'react';
import { useAuth } from '../context/AuthContext';
import { useAccountStorage } from './useAccountStorage';

// Bookmarks / reading history saved to the account on the server, so every
// device signed in with the same email shows the same list. The browser keeps
// a copy for instant display; the server copy wins whenever it loads.
// kind: 'bookmarks' | 'history'
export const syncedFlagKey = (email) => `librarySynced:${email.toLowerCase()}`;

export const useSyncedLibrary = (prefix, kind, fallback) => {
  const { user, getLibrary, importLibrary } = useAuth();
  const [list, setList] = useAccountStorage(prefix, fallback);
  const email = user?.email?.toLowerCase();
  // Changes made after a load started win over that load's (older) result.
  const version = useRef(0);

  const load = useCallback(async () => {
    if (!email || !getLibrary) return;
    const started = version.current;
    try {
      const flag = `${syncedFlagKey(email)}:${kind}`;
      let data;
      if (localStorage.getItem(flag)) {
        data = await getLibrary();
      } else {
        // First time on this device: add what it saved before to the account.
        let local = [];
        try { local = JSON.parse(localStorage.getItem(`${prefix}:${email}`)) || []; } catch { local = []; }
        data = await importLibrary({ [kind]: Array.isArray(local) ? local : [] });
        localStorage.setItem(flag, '1');
      }
      if (version.current === started && Array.isArray(data?.[kind])) setList(data[kind]);
    } catch {
      // Offline or server busy: keep showing this device's copy.
    }
  }, [email, kind, prefix, getLibrary, importLibrary, setList]);

  useEffect(() => {
    load();
    const onVisible = () => { if (document.visibilityState === 'visible') load(); };
    document.addEventListener('visibilitychange', onVisible);
    window.addEventListener('focus', onVisible);
    return () => {
      document.removeEventListener('visibilitychange', onVisible);
      window.removeEventListener('focus', onVisible);
    };
  }, [load]);

  // Update the local copy now and send the change to the server.
  const change = useCallback((updater, send) => {
    version.current += 1;
    setList(updater);
    if (email && send) Promise.resolve().then(send).catch(() => {});
  }, [email, setList]);

  return [list, change];
};
