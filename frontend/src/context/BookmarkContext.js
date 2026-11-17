import React, { createContext, useContext } from 'react';
import { useAccountStorage } from '../hooks/useAccountStorage';

const BookmarkContext = createContext();

const EMPTY = [];

export const BookmarkProvider = ({ children }) => {
  const [bookmarks, setBookmarks] = useAccountStorage('bookmarkedArticles', EMPTY);

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
