// Default catalog of trusted Malaysia English news platforms. Users can
// follow/unfollow any of these, add their own custom platforms, or remove
// platforms from the trusted list entirely (see TrustedPlatformsContext).

export const DEFAULT_TRUSTED_PLATFORMS = [
  { id: 'the-star', name: 'The Star', url: 'https://www.thestar.com.my' },
  { id: 'bernama', name: 'Bernama', url: 'https://www.bernama.com/en/' },
  { id: 'malay-mail', name: 'Malay Mail', url: 'https://www.malaymail.com' },
  { id: 'nst', name: 'New Straits Times', url: 'https://www.nst.com.my' },
  { id: 'fmt', name: 'Free Malaysia Today', url: 'https://www.freemalaysiatoday.com' },
  { id: 'edge-malaysia', name: 'The Edge Malaysia', url: 'https://theedgemalaysia.com' }
];

// Platforms followed by default for first-time users.
export const DEFAULT_FOLLOWED_IDS = DEFAULT_TRUSTED_PLATFORMS.map((p) => p.id);
