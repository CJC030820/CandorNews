import { useEffect, useState } from 'react';

// Empty string = same site (production behind the HTTPS proxy); unset = local dev backend.
const API_URL = process.env.REACT_APP_API_URL ?? 'http://localhost:8080';

// How long to wait for an image before trying the next source. Some
// publishers leave the connection hanging instead of refusing it, which would
// otherwise leave the card blank for a long time.
export const IMAGE_TIMEOUT_MS = 8000;

// Image sources to try in order: the publisher's own image, then the copy the
// backend stored when the article was collected (used when a publisher blocks
// the browser or the link breaks).
export const articleImageSources = (article = {}) => {
  if (!article.image) return [];
  const hasId = article.id !== undefined && article.id !== null;
  const stored = hasId ? `${API_URL}/api/articles/${encodeURIComponent(article.id)}/image` : null;
  // Prefer our own stored copy when the server has one: it does not depend on
  // the publisher being reachable or allowing the browser to load it.
  const order = article.imageStored ? [stored, article.image] : [article.image, stored];
  return order.filter(Boolean);
};

// Returns the current image URL (or null for the placeholder) plus onLoad and
// onError handlers. A source that neither loads nor fails within the timeout
// is skipped.
// The timer only starts once the image is on screen, because lazy-loaded
// images below the fold have not started downloading yet.
export const useArticleImage = (article) => {
  const sources = articleImageSources(article);
  const key = sources.join('|');
  const [index, setIndex] = useState(0);
  const [loaded, setLoaded] = useState(false);
  const [visible, setVisible] = useState(typeof IntersectionObserver === 'undefined');
  const [node, setNode] = useState(null);
  useEffect(() => { setIndex(0); setLoaded(false); }, [key]);
  useEffect(() => {
    if (!node || visible || typeof IntersectionObserver === 'undefined') return undefined;
    const observer = new IntersectionObserver((entries) => {
      if (entries.some((entry) => entry.isIntersecting)) setVisible(true);
    });
    observer.observe(node);
    return () => observer.disconnect();
  }, [node, visible]);
  const src = index < sources.length ? sources[index] : null;
  useEffect(() => {
    if (!src || loaded || !visible) return undefined;
    const timer = setTimeout(() => setIndex((current) => current + 1), IMAGE_TIMEOUT_MS);
    return () => clearTimeout(timer);
  }, [src, loaded, visible]);
  return {
    src,
    ref: setNode,
    onLoad: () => setLoaded(true),
    onError: () => setIndex((current) => current + 1),
  };
};
