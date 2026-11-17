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
    ['bookmarkedArticles', 'readArticleHistory', 'followedPlatformIds'].forEach(key =>
      localStorage.removeItem(`${key}:${user.email.toLowerCase()}`));
    logout(); return true;
  };
  const getFeed = useCallback(async ({topic, limit} = {}) =>
    (await api.get('/api/articles/feed', {params: {topic: topic === 'all' ? undefined : topic, limit}})).data, [api]);
  const getArticle = useCallback(async id => (await api.get(`/api/articles/${encodeURIComponent(id)}`)).data, [api]);
  const refreshFeed = useCallback(async platforms => (await api.post('/api/articles/refresh', {platforms})).data, [api]);
  const getRefreshStatus = useCallback(async id => (await api.get(`/api/articles/refresh/${encodeURIComponent(id)}`)).data, [api]);
  const selectedTopics = user?.preferred_topics || [];
  return <AuthContext.Provider value={{token,user,loading,topicsCompleted:selectedTopics.length > 0,selectedTopics,
    login,logout,register,updatePreferences,updateProfile,completeTopicSelection:updatePreferences,
    getSelectedTopics:() => selectedTopics,getEmailStatus,updateEmailSettings,sendEmailTest,requestEmailVerification,confirmEmailVerification,deleteAccount,
    getFeed,getArticle,refreshFeed,getRefreshStatus}}>{!loading && children}</AuthContext.Provider>;
};
export const useAuth = () => useContext(AuthContext);
