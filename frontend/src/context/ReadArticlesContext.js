import React, { createContext, useContext, useCallback } from 'react';
import { useAuth } from './AuthContext';
import { useSyncedLibrary } from '../hooks/useSyncedLibrary';

const ReadArticlesContext = createContext();

const EMPTY = [];
const same = (a, b) => String(a) === String(b);

// Reading history is saved to the account, so the PC and phone show the same list.
export const ReadArticlesProvider = ({ children }) => {
  const { saveLibraryItem, removeLibraryItem, clearLibrary } = useAuth();
  const [history, change] = useSyncedLibrary('readArticleHistory', 'history', EMPTY);

  const isRead = useCallback((articleId) => {
    if (articleId === undefined || articleId === null) return false;
    return history.some((entry) => same(entry.id, articleId));
  }, [history]);

  // Every view moves the article to the top of History with a fresh time.
  const markAsRead = useCallback((article) => {
    if (!article || article.id === undefined || article.id === null) return;
    const entry = { ...article, readAt: new Date().toISOString() };
    change((prev) => [entry, ...prev.filter((e) => !same(e.id, article.id))],
      () => saveLibraryItem('history', entry));
  }, [change, saveLibraryItem]);

  const removeFromHistory = useCallback((articleId) => {
    change((prev) => prev.filter((e) => !same(e.id, articleId)),
      () => removeLibraryItem('history', articleId));
  }, [change, removeLibraryItem]);

  const clearHistory = useCallback(() => {
    change(() => [], () => clearLibrary('history'));
  }, [change, clearLibrary]);

  const value = {
    history,
    readArticleIds: history.map((entry) => entry.id),
    readCount: history.length,
    isRead,
    markAsRead,
    removeFromHistory,
    clearHistory
  };

  return (
    <ReadArticlesContext.Provider value={value}>
      {children}
    </ReadArticlesContext.Provider>
  );
};

export const useReadArticles = () => {
  const context = useContext(ReadArticlesContext);
  if (!context) {
    throw new Error('useReadArticles must be used within a ReadArticlesProvider');
  }
  return context;
};
