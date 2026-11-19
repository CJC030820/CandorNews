import React, { createContext, useContext, useEffect, useRef, useCallback } from 'react';
import { useAuth } from './AuthContext';
import { useAccountStorage } from '../hooks/useAccountStorage';
import { DEFAULT_TRUSTED_PLATFORMS, DEFAULT_FOLLOWED_IDS } from '../constants/platforms';

const TrustedPlatformsContext = createContext();

const VALID_IDS = new Set(DEFAULT_TRUSTED_PLATFORMS.map((p) => p.id));
const clean = (ids) => (Array.isArray(ids) ? ids.filter((id) => VALID_IDS.has(id)) : []);
const sameIds = (a, b) => a.length === b.length && a.every((id) => b.includes(id));

// Followed publishers are saved to the account, so every device signed in
// with the same email follows the same publishers. The browser keeps a copy
// for instant display.
export const TrustedPlatformsProvider = ({ children }) => {
  const { user, updateFollowedPlatforms } = useAuth();
  // The catalog of trusted platforms is fixed by the system - users can only
  // choose which of these to follow.
  const platforms = DEFAULT_TRUSTED_PLATFORMS;
  const [stored, setStored] = useAccountStorage('followedPlatformIds', DEFAULT_FOLLOWED_IDS);
  const followedIds = clean(stored).length ? clean(stored) : DEFAULT_FOLLOWED_IDS;
  const serverIds = user?.followed_platforms;
  const migrated = useRef(null);

  useEffect(() => {
    if (!user || !updateFollowedPlatforms) return;
    if (Array.isArray(serverIds)) {
      // The account copy wins (it may have been changed on another device).
      const fromServer = clean(serverIds);
      if (fromServer.length && !sameIds(fromServer, clean(stored))) setStored(fromServer);
    } else if (migrated.current !== user.email) {
      // First visit since followed publishers moved to the account: save this device's choice.
      migrated.current = user.email;
      updateFollowedPlatforms(followedIds).catch(() => {});
    }
    // Runs when the account copy changes; local edits are sent by save().
  }, [user, serverIds]);

  const save = useCallback((next) => {
    if (!next.length) return;
    setStored(next);
    if (updateFollowedPlatforms) updateFollowedPlatforms(next).catch(() => {});
  }, [setStored, updateFollowedPlatforms]);

  const isFollowing = (platformId) => followedIds.includes(platformId);

  const followPlatform = (platformId) => {
    if (!VALID_IDS.has(platformId) || followedIds.includes(platformId)) return;
    save([...followedIds, platformId]);
  };

  const unfollowPlatform = (platformId) => {
    if (followedIds.length <= 1) return;
    save(followedIds.filter((id) => id !== platformId));
  };

  const toggleFollow = (platformId) => {
    if (isFollowing(platformId)) unfollowPlatform(platformId);
    else followPlatform(platformId);
  };

  // Reset the followed list back to the system defaults.
  const resetToDefaults = () => save(DEFAULT_FOLLOWED_IDS);

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
