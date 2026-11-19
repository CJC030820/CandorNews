import React, { createContext, useContext, useCallback } from 'react';
import { useAuth } from './AuthContext';
import { useSyncedLibrary } from '../hooks/useSyncedLibrary';

const BookmarkContext = createContext();

const EMPTY = [];
const same = (a, b) => String(a) === String(b);

// Bookmarks are saved to the account, so the PC and phone show the same list.
export const BookmarkProvider = ({ children }) => {
  const { saveLibraryItem, removeLibraryItem } = useAuth();
  const [bookmarks, change] = useSyncedLibrary('bookmarkedArticles', 'bookmarks', EMPTY);

  const isBookmarked = useCallback((articleId) => bookmarks.some((a) => same(a.id, articleId)), [bookmarks]);

  const addBookmark = useCallback((article) => {
    if (!article || article.id === undefined || article.id === null) return;
    const entry = { ...article, savedAt: new Date().toISOString() };
    change((prev) => (prev.some((a) => same(a.id, article.id)) ? prev : [entry, ...prev]),
      () => saveLibraryItem('bookmarks', entry));
  }, [change, saveLibraryItem]);

  const removeBookmark = useCallback((articleId) => {
    change((prev) => prev.filter((a) => !same(a.id, articleId)),
      () => removeLibraryItem('bookmarks', articleId));
  }, [change, removeLibraryItem]);

  const toggleBookmark = useCallback((article) => {
    if (isBookmarked(article.id)) removeBookmark(article.id);
    else addBookmark(article);
  }, [isBookmarked, addBookmark, removeBookmark]);

  const value = { bookmarks, isBookmarked, addBookmark, removeBookmark, toggleBookmark };

  return (
    <BookmarkContext.Provider value={value}>
      {children}
    </BookmarkContext.Provider>
  );
};

export const useBookmarks = () => {
  const context = useContext(BookmarkContext);
  if (!context) {
    throw new Error('useBookmarks must be used within a BookmarkProvider');
  }
  return context;
};
