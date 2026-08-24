import React, { createContext, useContext, useState, useEffect } from 'react';
import { DEFAULT_TRUSTED_PLATFORMS, DEFAULT_FOLLOWED_IDS } from '../constants/platforms';

const TrustedPlatformsContext = createContext();

const FOLLOWED_STORAGE_KEY = 'followedPlatformIds';

const getFollowedIdsFromStorage = () => {
  try {
    const stored = localStorage.getItem(FOLLOWED_STORAGE_KEY);
    if (!stored) return DEFAULT_FOLLOWED_IDS;
    const parsed = JSON.parse(stored);
    // Guard against stale IDs from a previous session that no longer exist
    // in the fixed system catalog.
    const validIds = new Set(DEFAULT_TRUSTED_PLATFORMS.map((p) => p.id));
    return parsed.filter((id) => validIds.has(id));
  } catch (e) {
    console.error('Error parsing followed platforms from localStorage:', e);
    return DEFAULT_FOLLOWED_IDS;
  }
};

export const TrustedPlatformsProvider = ({ children }) => {
  // The catalog of trusted platforms is fixed by the system - users can only
  // choose which of these to follow, not add their own websites or remove
  // platforms from the list.
  const platforms = DEFAULT_TRUSTED_PLATFORMS;

  // Which platform IDs the user is currently following.
  const [followedIds, setFollowedIds] = useState(getFollowedIdsFromStorage);

  useEffect(() => {
    localStorage.setItem(FOLLOWED_STORAGE_KEY, JSON.stringify(followedIds));
  }, [followedIds]);

  const isFollowing = (platformId) => followedIds.includes(platformId);

  const followPlatform = (platformId) => {
    if (!platforms.some((p) => p.id === platformId)) return;
    setFollowedIds((prev) => (prev.includes(platformId) ? prev : [...prev, platformId]));
  };

  const unfollowPlatform = (platformId) => {
    setFollowedIds((prev) => prev.filter((id) => id !== platformId));
  };

  const toggleFollow = (platformId) => {
    if (isFollowing(platformId)) {
      unfollowPlatform(platformId);
    } else {
      followPlatform(platformId);
    }
  };

  // Reset the followed list back to the system defaults.
  const resetToDefaults = () => {
    setFollowedIds(DEFAULT_FOLLOWED_IDS);
  };

  const followedPlatforms = platforms.filter((p) => followedIds.includes(p.id));

  const value = {
    platforms,
    followedIds,
    followedPlatforms,
    isFollowing,
    followPlatform,
    unfollowPlatform,
    toggleFollow,
    resetToDefaults
  };

  return (
    <TrustedPlatformsContext.Provider value={value}>
      {children}
    </TrustedPlatformsContext.Provider>
  );
};

export const useTrustedPlatforms = () => {
  const context = useContext(TrustedPlatformsContext);
  if (!context) {
    throw new Error('useTrustedPlatforms must be used within a TrustedPlatformsProvider');
  }
  return context;
};
