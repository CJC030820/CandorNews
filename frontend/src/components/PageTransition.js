import React, { useEffect, useState } from 'react';
import { useLocation } from 'react-router-dom';
import './PageTransition.css';

/**
 * PageTransition Wrapper
 * Provides smooth fade in/out animations when routes change
 */
const PageTransition = ({ children }) => {
  const location = useLocation();
  const [isVisible, setIsVisible] = useState(true);
  const [displayKey, setDisplayKey] = useState(location.pathname);

  useEffect(() => {
    if (location.pathname !== displayKey) {
      // Route changed - start fade out
      setIsVisible(false);
      
      // After fade out completes, update the display and fade in
      const timer = setTimeout(() => {
        setDisplayKey(location.pathname);
        setIsVisible(true);
      }, 300); // Match CSS animation duration
      
      return () => clearTimeout(timer);
    }
  }, [location.pathname, displayKey]);

  return (
    <div 
      className={`page-transition ${isVisible ? 'visible' : 'hidden'}`}
    >
      {children}
    </div>
  );
};

export default PageTransition;
