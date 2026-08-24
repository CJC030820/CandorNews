import React, { useState, useEffect } from 'react';
import './BackToTopButton.css';

const BackToTopButton = () => {
  const [isVisible, setIsVisible] = useState(false);

  // Show button when page is scrolled down
  const toggleVisibility = () => {
    const scrollPosition = window.scrollY || window.pageYOffset || document.documentElement.scrollTop;
    console.log('Current scroll position:', scrollPosition, 'Visible:', scrollPosition > 300);
    if (scrollPosition > 300) {
      setIsVisible(true);
    } else {
      setIsVisible(false);
    }
  };

  // Scroll to top smoothly
  const scrollToTop = () => {
    window.scrollTo({
      top: 0,
      behavior: 'smooth'
    });
  };

  useEffect(() => {
    // Add scroll listener with passive flag for better performance
    window.addEventListener('scroll', toggleVisibility, { passive: true });
    
    // Check initial scroll position on mount
    toggleVisibility();
    
    return () => window.removeEventListener('scroll', toggleVisibility);
  }, []);

  return (
    <button
      className={`back-to-top-btn ${isVisible ? 'visible' : ''}`}
      onClick={scrollToTop}
      title="Back to top"
      aria-label="Back to top"
      style={{
        display: isVisible ? 'flex' : 'none'
      }}
    >
      ↑
    </button>
  );
};

export default BackToTopButton;
