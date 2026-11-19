import React, { createContext, useContext, useState, useEffect, useMemo, useCallback } from 'react';
import axios from 'axios';

const AuthContext = createContext();
// Empty string = same site (production behind the HTTPS proxy); unset = local dev backend.
const API_URL = process.env.REACT_APP_API_URL ?? 'http://localhost:8080';

export const AuthProvider = ({ children }) => {
  const [token, setToken] = useState(localStorage.getItem('token') || '');
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const api = useMemo(() => axios.create({ baseURL: API_URL, timeout: 15000,
    headers: token ? { Authorization: `Bearer ${token}` } : {} }), [token]);
  const logout = useCallback(() => {
    setToken(''); setUser(null); localStorage.removeItem('token');
    sessionStorage.removeItem('feedArticles');
  }, []);

  useEffect(() => {
    let active = true;
    if (!token) { setLoading(false); return; }
    api.get('/api/auth/me').then(({data}) => { if (active) setUser(data); })
      .catch(error => { if (active && error.response?.status === 401) logout(); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [api, token, logout]);

  // Coming back to the tab: reload the profile so settings changed on
  // another device (followed publishers, interests) show here too.
  useEffect(() => {
    if (!token) return undefined;
    const refresh = () => {
      if (document.visibilityState !== 'visible') return;
      api.get('/api/auth/me').then(({data}) => setUser(data))
        .catch(error => { if (error.response?.status === 401) logout(); });
    };
    document.addEventListener('visibilitychange', refresh);
    return () => document.removeEventListener('visibilitychange', refresh);
  }, [api, token, logout]);

  const login = async (email, password) => {
    try {
      const { data } = await api.post('/api/auth/login', { email, password });
      const profile = await api.get('/api/auth/me', { headers: { Authorization: `Bearer ${data.access_token}` } });
      localStorage.setItem('token', data.access_token);
      setToken(data.access_token); setUser(profile.data);
      return true;
    } catch { return false; }
  };
  const register = async (name, email, password) => (await api.post('/api/auth/register', {name,email,password})).data;
  const updatePreferences = async preferred_topics => {
    const {data} = await api.put('/api/users/preferences', {preferred_topics}); setUser(data); return data;
  };
  const updateProfile = async name => {
    const {data} = await api.put('/api/users/profile', {name}); setUser(data); return data;
  };
  const getEmailStatus = async () => (await api.get('/api/notifications/email/status')).data;
  const updateEmailSettings = async ({emailNotificationsEnabled, emailNotificationSchedule, emailNotificationTimes}) => {
    const {data} = await api.put('/api/notifications/email', {
      email_notifications_enabled: emailNotificationsEnabled, email_notification_schedule: emailNotificationSchedule,
      email_notification_times: emailNotificationTimes});
    setUser(data); return data;
  };
  const sendEmailTest = async message => (await api.post('/api/notifications/email/test', {message})).data;
  const requestEmailVerification = async () => (await api.post('/api/notifications/email/verification')).data;
  const confirmEmailVerification = async code => {
    const {data} = await api.post('/api/notifications/email/verification/confirm', {code}); setUser(data); return data;
  };
  const deleteAccount = async password => {
    await api.delete('/api/users/me', {data: {password}});
    const email = user.email.toLowerCase();
    ['bookmarkedArticles', 'readArticleHistory', 'followedPlatformIds'].forEach(key => localStorage.removeItem(`${key}:${email}`));
    ['bookmarks', 'history'].forEach(kind => localStorage.removeItem(`librarySynced:${email}:${kind}`));
    logout(); return true;
  };
  const getFeed = useCallback(async ({topic, limit} = {}) =>
    (await api.get('/api/articles/feed', {params: {topic: topic === 'all' ? undefined : topic, limit}})).data, [api]);
  const getArticle = useCallback(async id => (await api.get(`/api/articles/${encodeURIComponent(id)}`)).data, [api]);
  const refreshFeed = useCallback(async platforms => (await api.post('/api/articles/refresh', {platforms})).data, [api]);
  const getRefreshStatus = useCallback(async id => (await api.get(`/api/articles/refresh/${encodeURIComponent(id)}`)).data, [api]);
  // Bookmarks and history saved to the account (shared by all devices). kind: 'bookmarks' | 'history'
  const getLibrary = useCallback(async () => (await api.get('/api/me/library')).data, [api]);
  const importLibrary = useCallback(async lists => (await api.post('/api/me/library/import', lists)).data, [api]);
  const saveLibraryItem = useCallback(async (kind, article) =>
    (await api.put(`/api/me/${kind}/${encodeURIComponent(article.id)}`, {article})).data, [api]);
  const removeLibraryItem = useCallback(async (kind, id) =>
    (await api.delete(`/api/me/${kind}/${encodeURIComponent(id)}`)).data, [api]);
  const clearLibrary = useCallback(async kind => (await api.delete(`/api/me/${kind}`)).data, [api]);
  // Followed publishers saved to the account (shared by all devices).
  const updateFollowedPlatforms = useCallback(async platformIds => {
    const {data} = await api.put('/api/users/platforms', {platform_ids: platformIds}); setUser(data); return data;
  }, [api]);
  // Search every stored article, not only the latest loaded batch.
  const searchArticles = useCallback(async (q, limit = 100) =>
    (await api.get('/api/articles/search', {params: {q, limit}})).data, [api]);
  const selectedTopics = user?.preferred_topics || [];
  return <AuthContext.Provider value={{token,user,loading,topicsCompleted:selectedTopics.length > 0,selectedTopics,
    login,logout,register,updatePreferences,updateProfile,completeTopicSelection:updatePreferences,
    getSelectedTopics:() => selectedTopics,getEmailStatus,updateEmailSettings,sendEmailTest,requestEmailVerification,confirmEmailVerification,deleteAccount,
    getFeed,getArticle,refreshFeed,getRefreshStatus,getLibrary,importLibrary,saveLibraryItem,removeLibraryItem,clearLibrary,updateFollowedPlatforms,searchArticles}}>{!loading && children}</AuthContext.Provider>;
};
export const useAuth = () => useContext(AuthContext);
