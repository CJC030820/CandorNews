import React from 'react';
import { render, act, waitFor } from '@testing-library/react';
import { TrustedPlatformsProvider, useTrustedPlatforms } from './TrustedPlatformsContext';

const mockAuth = { user: { email: 'same@example.com', followed_platforms: null } };
jest.mock('./AuthContext', () => ({ useAuth: () => mockAuth }));

let api;
const Probe = () => { api = useTrustedPlatforms(); return <p>{api.followedIds.join(',')}</p>; };
const open = () => render(<TrustedPlatformsProvider><Probe /></TrustedPlatformsProvider>);

beforeEach(() => {
  localStorage.clear();
  mockAuth.user = { email: 'same@example.com', followed_platforms: null };
  mockAuth.updateFollowedPlatforms = jest.fn(async (ids) => ({ followed_platforms: ids }));
});

test('this device\'s choice is saved to the account the first time', async () => {
  localStorage.setItem('followedPlatformIds:same@example.com', JSON.stringify(['nst']));
  open();
  await waitFor(() => expect(mockAuth.updateFollowedPlatforms).toHaveBeenCalledWith(['nst']));
});

test('the account choice from another device is used here', () => {
  localStorage.setItem('followedPlatformIds:same@example.com', JSON.stringify(['bernama', 'nst', 'fmt']));
  mockAuth.user = { email: 'same@example.com', followed_platforms: ['fmt'] };
  const { container } = open();
  expect(container.textContent).toBe('fmt');
  expect(mockAuth.updateFollowedPlatforms).not.toHaveBeenCalled();
});

test('following and unfollowing is sent to the account, and the last one cannot be removed', () => {
  mockAuth.user = { email: 'same@example.com', followed_platforms: ['nst', 'fmt'] };
  open();
  act(() => api.toggleFollow('nst'));
  expect(mockAuth.updateFollowedPlatforms).toHaveBeenLastCalledWith(['fmt']);
  act(() => api.toggleFollow('fmt'));
  expect(mockAuth.updateFollowedPlatforms).toHaveBeenCalledTimes(1);
});
