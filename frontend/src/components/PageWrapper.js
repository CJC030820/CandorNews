import React from 'react';
import './PageWrapper.css';

/**
 * PageWrapper
 * Wraps individual page content with animation support
 * Apply to the root container of each page for consistent animations
 */
const PageWrapper = ({ children, className = '' }) => {
  return (
    <div className={`page-wrapper ${className}`}>
      {children}
    </div>
  );
};

export default PageWrapper;
