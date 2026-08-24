import React, { createContext, useContext, useState, useEffect } from 'react';

const BookmarkContext = createContext();

const STORAGE_KEY = 'bookmarkedArticles';

const getBookmarksFromStorage = () => {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    return stored ? JSON.parse(stored) : [];
  } catch (e) {
    console.error('Error parsing bookmarks from localStorage:', e);
    return [];
  }
};

export const BookmarkProvider = ({ children }) => {
  const [bookmarks, setBookmarks] = useState(getBookmarksFromStorage);

  // Persist to localStorage whenever bookmarks change
  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(bookmarks));
  }, [bookmarks]);

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
