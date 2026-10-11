import { useEffect, useRef } from 'react';

/**
 * Custom hook to create an overscroll bounce effect
 * Adds visual feedback when user scrolls past the boundaries
 */
export const useOverscrollBounce = (elementRef) => {
  const touchStartY = useRef(0);
  const scrollVelocity = useRef(0);

  useEffect(() => {
    const element = elementRef?.current || window;
    if (!element) return;

    let isOverscrolling = false;
    let overscrollAmount = 0;
    let animationFrameId = null;

    const handleTouchStart = (e) => {
      touchStartY.current = e.touches[0].clientY;
      scrollVelocity.current = 0;
      isOverscrolling = false;
      overscrollAmount = 0;
    };

    const handleTouchMove = (e) => {
      if (animationFrameId) {
        cancelAnimationFrame(animationFrameId);
      }

      const target = element === window ? document.documentElement : element;
      const currentY = e.touches[0].clientY;
      const delta = currentY - touchStartY.current;

      scrollVelocity.current = delta;

      // Check if at top or bottom
      const isAtTop = target.scrollTop === 0 && delta > 0;
      const isAtBottom =
        target.scrollHeight - target.scrollTop - target.clientHeight < 1 &&
        delta < 0;

      if (isAtTop || isAtBottom) {
        isOverscrolling = true;
        overscrollAmount = Math.abs(delta);

        // Apply visual effect
        applyOverscrollEffect(element, overscrollAmount, isAtTop ? 'top' : 'bottom');
      } else {
        isOverscrolling = false;
        resetOverscrollEffect(element);
      }
    };

    const handleTouchEnd = () => {
      if (isOverscrolling) {
        // Animate back to original position (bounce effect)
        animateBounceback(element, overscrollAmount);
      }
      isOverscrolling = false;
      overscrollAmount = 0;
    };

    const applyOverscrollEffect = (elem, amount, position) => {
      const scale = 1 - Math.min(amount / 200, 0.05); // Max 5% scale reduction
      const opacity = Math.max(0.3, 1 - amount / 500); // Fade effect

      if (elem === window) {
        document.body.style.transform = `scale(${scale})`;
        document.body.style.transformOrigin =
          position === 'top' ? 'center top' : 'center bottom';
        document.body.style.opacity = opacity;
      } else {
        elem.style.transform = `scale(${scale})`;
        elem.style.transformOrigin =
          position === 'top' ? 'center top' : 'center bottom';
        elem.style.opacity = opacity;
      }
    };

    const resetOverscrollEffect = (elem) => {
      if (elem === window) {
        document.body.style.transform = 'scale(1)';
        document.body.style.opacity = '1';
      } else {
        elem.style.transform = 'scale(1)';
        elem.style.opacity = '1';
      }
    };

    const animateBounceback = (elem, startAmount) => {
      let currentAmount = startAmount;
      const target = elem === window ? document.documentElement : elem;
      const isAtTop = target.scrollTop === 0;

      const animate = () => {
        // Exponential decay
        currentAmount *= 0.85;

        if (currentAmount > 0.1) {
          applyOverscrollEffect(elem, currentAmount, isAtTop ? 'top' : 'bottom');
          animationFrameId = requestAnimationFrame(animate);
        } else {
          resetOverscrollEffect(elem);
        }
      };

      animationFrameId = requestAnimationFrame(animate);
    };

    if (element === window) {
      window.addEventListener('touchstart', handleTouchStart, false);
      window.addEventListener('touchmove', handleTouchMove, false);
      window.addEventListener('touchend', handleTouchEnd, false);

      return () => {
        window.removeEventListener('touchstart', handleTouchStart);
        window.removeEventListener('touchmove', handleTouchMove);
        window.removeEventListener('touchend', handleTouchEnd);
        if (animationFrameId) {
          cancelAnimationFrame(animationFrameId);
        }
      };
    } else {
      element.addEventListener('touchstart', handleTouchStart, false);
      element.addEventListener('touchmove', handleTouchMove, false);
      element.addEventListener('touchend', handleTouchEnd, false);

      return () => {
        element.removeEventListener('touchstart', handleTouchStart);
        element.removeEventListener('touchmove', handleTouchMove);
        element.removeEventListener('touchend', handleTouchEnd);
        if (animationFrameId) {
          cancelAnimationFrame(animationFrameId);
        }
      };
    }
  }, [elementRef]);
};
