import React, { createContext, useContext, useState, useEffect } from 'react';
import { useAuth } from './AuthContext';

const BookmarkContext = createContext();

const STORAGE_KEY = 'bookmarkedArticles';

const getStorageKey = (email) => email ? `${STORAGE_KEY}:${email.toLowerCase()}` : null;

const getBookmarksFromStorage = (email) => {
  try {
    const key = getStorageKey(email);
    if (!key) return [];
    const stored = localStorage.getItem(key);
    return stored ? JSON.parse(stored) : [];
  } catch (e) {
    console.error('Error parsing bookmarks from localStorage:', e);
    return [];
  }
};

export const BookmarkProvider = ({ children }) => {
  const { user } = useAuth();
  const accountEmail = user?.email || null;
  const [bookmarks, setBookmarks] = useState([]);

  useEffect(() => {
    setBookmarks(getBookmarksFromStorage(accountEmail));
  }, [accountEmail]);

  // Persist bookmarks under the signed-in account, never under one shared key.
  useEffect(() => {
    const key = getStorageKey(accountEmail);
    if (key) localStorage.setItem(key, JSON.stringify(bookmarks));
  }, [accountEmail, bookmarks]);

  const isBookmarked = (articleId) => {
    return bookmarks.some((a) => a.id === articleId);
  };

  const addBookmark = (article) => {
    setBookmarks((prev) => {
      if (prev.some((a) => a.id === article.id)) return prev;
      return [...prev, article];
    });
  };

  const removeBookmark = (articleId) => {
    setBookmarks((prev) => prev.filter((a) => a.id !== articleId));
  };

  const toggleBookmark = (article) => {
    if (isBookmarked(article.id)) {
      removeBookmark(article.id);
    } else {
      addBookmark(article);
    }
  };

  const value = {
    bookmarks,
    isBookmarked,
    addBookmark,
    removeBookmark,
    toggleBookmark
  };

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
