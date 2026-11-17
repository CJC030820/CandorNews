import React, { useState, useRef, useEffect } from 'react';
import './ShareMenu.css';

/**
 * Reusable share button + menu.
 * Everything shared is the article headline plus its CandorNews page link
 * (shareUrl); the publisher's original link is never shared.
 *
 * Uses the native share sheet when available (phones); otherwise a dropdown
 * offers "copy link" and share targets.
 *
 * Props:
 *  - article: { id, title }
 *  - variant: 'icon' (small round button, for cards) | 'button' (labeled button, for detail page)
 */
const ShareMenu = ({ article, variant = 'button' }) => {
  const [menuOpen, setMenuOpen] = useState(false);
  const [copiedKey, setCopiedKey] = useState(null);
  const containerRef = useRef(null);

  const shareUrl = `${window.location.origin}/article/${article.id}`;
  const shareTitle = article.title || 'Check out this article';
  // Shares contain only the headline and the CandorNews link.
  const shareMessage = `${shareTitle}\n${shareUrl}`;

  useEffect(() => {
    if (!menuOpen) return;
    const handleClickOutside = (e) => {
      if (containerRef.current && !containerRef.current.contains(e.target)) {
        setMenuOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [menuOpen]);

  const canUseNativeShare = typeof navigator !== 'undefined' && !!navigator.share;

  const handleShareClick = async (e) => {
    e.stopPropagation();

    if (canUseNativeShare) {
      try {
        await navigator.share({
          title: shareTitle,
          text: shareTitle,
          url: shareUrl
        });
      } catch (err) {
        // User cancelled the share sheet, or it failed — no action needed
      }
      return;
    }

    setMenuOpen((prev) => !prev);
  };

  const handleCopyLink = async (e, url, key) => {
    e.stopPropagation();
    try {
      await navigator.clipboard.writeText(url);
      setCopiedKey(key);
      setTimeout(() => setCopiedKey(null), 2000);
    } catch (err) {
      console.error('Failed to copy link:', err);
    }
  };

  const openShareWindow = (e, url) => {
    e.stopPropagation();
    window.open(url, '_blank', 'noopener,noreferrer,width=600,height=500');
    setMenuOpen(false);
  };

  // Every target receives only the headline and the CandorNews link.
  const shareLinks = [
    {
      name: 'Twitter / X',
      icon: '🐦',
      url: `https://twitter.com/intent/tweet?text=${encodeURIComponent(shareTitle)}&url=${encodeURIComponent(shareUrl)}`
    },
    {
      name: 'Facebook',
      icon: '📘',
      url: `https://www.facebook.com/sharer/sharer.php?u=${encodeURIComponent(shareUrl)}`
    },
    {
      name: 'LinkedIn',
      icon: '💼',
      url: `https://www.linkedin.com/sharing/share-offsite/?url=${encodeURIComponent(shareUrl)}`
    },
    {
      name: 'Email',
      icon: '✉️',
      url: `mailto:?subject=${encodeURIComponent(shareTitle)}&body=${encodeURIComponent(shareMessage)}`
    }
  ];

  return (
    <div className={`share-menu-container variant-${variant}`} ref={containerRef}>
      <button
        className={variant === 'icon' ? 'share-toggle' : 'share-btn'}
        onClick={handleShareClick}
        title="Share this article"
        aria-label="Share this article"
      >
        {variant === 'icon' ? (
          <span className="share-toggle-icon">📤</span>
        ) : (
          '📤 Share'
        )}
      </button>

      {menuOpen && !canUseNativeShare && (
        <div className="share-dropdown" onClick={(e) => e.stopPropagation()}>
          <button
            className="share-option copy-link"
            onClick={(e) => handleCopyLink(e, shareMessage, 'site')}
          >
            <span className="share-option-icon">{copiedKey === 'site' ? '✅' : '🔗'}</span>
            {copiedKey === 'site' ? 'Copied!' : 'Copy title and link'}
          </button>

          <div className="share-divider" />
          {shareLinks.map((link) => (
            <button
              key={link.name}
              className="share-option"
              onClick={(e) => openShareWindow(e, link.url)}
            >
              <span className="share-option-icon">{link.icon}</span>
              {link.name}
            </button>
          ))}

        </div>
      )}
    </div>
  );
};

export default ShareMenu;
