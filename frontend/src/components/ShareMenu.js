import React, { useState, useRef, useEffect } from 'react';
import './ShareMenu.css';

/**
 * Reusable share button + menu.
 * Offers two distinct links to share:
 *  1. "My site" link - the CandorNews article detail page (shareUrl)
 *  2. "Original source" link - the original publisher's article (originalUrl)
 *
 * Uses the native Web Share API when available (mobile/supported browsers) -
 * shares the CandorNews link by default there, since native share sheets only
 * accept a single URL. The dropdown fallback (desktop) exposes both links
 * individually so the user can pick whichever they want to copy/share.
 *
 * Props:
 *  - article: { id, title, description, url } - article.url is the original
 *    source article's URL (e.g. the NST/FMT/Bernama article page)
 *  - variant: 'icon' (small round button, for cards) | 'button' (labeled button, for detail page)
 */
const ShareMenu = ({ article, variant = 'button' }) => {
  const [menuOpen, setMenuOpen] = useState(false);
  const [copiedKey, setCopiedKey] = useState(null);
  const containerRef = useRef(null);

  const shareUrl = `${window.location.origin}/article/${article.id}`;
  const originalUrl = article.url || null;
  const shareTitle = article.title || 'Check out this article';
  const shareText = article.description
    ? `${article.title} — ${article.description}`
    : article.title;

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
          text: shareText,
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

  // Social share links include both URLs in the shared text/body where the
  // platform supports more than a single link (Email); link-only platforms
  // (Twitter/Facebook/LinkedIn) use the CandorNews link as the primary share
  // target since that's the canonical page for this article on our site.
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
      url: `mailto:?subject=${encodeURIComponent(shareTitle)}&body=${encodeURIComponent(
        `${shareText}\n\nRead on CandorNews: ${shareUrl}` +
        (originalUrl ? `\nOriginal source: ${originalUrl}` : '')
      )}`
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
            onClick={(e) => handleCopyLink(e, shareUrl, 'site')}
          >
            <span className="share-option-icon">{copiedKey === 'site' ? '✅' : '🔗'}</span>
            {copiedKey === 'site' ? 'CandorNews link copied!' : 'Copy CandorNews link'}
          </button>

          {originalUrl && (
            <button
              className="share-option copy-link"
              onClick={(e) => handleCopyLink(e, originalUrl, 'original')}
            >
              <span className="share-option-icon">{copiedKey === 'original' ? '✅' : '🌐'}</span>
              {copiedKey === 'original' ? 'Original link copied!' : 'Copy original source link'}
            </button>
          )}

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

          {originalUrl && (
            <>
              <div className="share-divider" />
              <a
                className="share-option share-option-link"
                href={originalUrl}
                target="_blank"
                rel="noopener noreferrer"
                onClick={(e) => e.stopPropagation()}
              >
                <span className="share-option-icon">↗️</span>
                Open original article
              </a>
            </>
          )}
        </div>
      )}
    </div>
  );
};

export default ShareMenu;
