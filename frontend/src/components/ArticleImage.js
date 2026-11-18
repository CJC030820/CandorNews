import React from 'react';
import { useArticleImage } from '../utils/articleImage';
import './ArticleImage.css';

// "BERNAMA - English Version" -> "Bernama", "Business – Free Malaysia Today (FMT)" -> "Free Malaysia Today"
export const publisherName = (source = '') => {
  const s = source.toLowerCase();
  if (s.includes('bernama')) return 'Bernama';
  if (s.includes('free malaysia today') || s.includes('fmt')) return 'Free Malaysia Today';
  if (s.includes('new straits times') || s.includes('nst')) return 'New Straits Times';
  return source || 'CandorNews';
};

// Shown when an article has no usable image, so a picture area is never empty or broken.
export const ImagePlaceholder = ({ article = {}, compact = false }) => {
  const name = publisherName(article.source);
  const category = (article.categories && article.categories[0]) || article.category;
  return (
    <div className={`image-placeholder-card${compact ? ' compact' : ''}`} role="img" aria-label={`${name} news`}>
      <span className="placeholder-source">{name}</span>
      {!compact && category && <span className="placeholder-category">{category}</span>}
    </div>
  );
};

// Article picture with fallbacks: stored copy / publisher image, then the placeholder.
const ArticleImage = ({ article = {}, className = '', compact = false }) => {
  const { src, ref, onError, onLoad } = useArticleImage(article);
  return (
    <div className={`article-image-frame ${className}`} ref={ref}>
      {src ? (
        <img src={src} alt={article.title || ''} onError={onError} onLoad={onLoad} loading="lazy" />
      ) : (
        <ImagePlaceholder article={article} compact={compact} />
      )}
    </div>
  );
};

export default ArticleImage;
