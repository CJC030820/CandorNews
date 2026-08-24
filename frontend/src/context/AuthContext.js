import React, { createContext, useContext, useState, useEffect } from 'react';
import axios from 'axios';

const AuthContext = createContext();

export const AuthProvider = ({ children }) => {
  const [token, setToken] = useState(localStorage.getItem('token') || '');
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  // Whether the user has completed topic selection is derived directly from
  // the persisted user profile (preferred_topics stored in MongoDB), so it
  // is remembered across devices/sessions and the topic-selection page is
  // skipped automatically once topics exist - no localStorage needed.
  const topicsCompleted = !!(user && user.preferred_topics && user.preferred_topics.length > 0);
  const selectedTopics = user?.preferred_topics || [];

  // Load user when token changes
  useEffect(() => {
    const loadUser = async () => {
      if (token) {
        try {
          // Set authorization header
          axios.defaults.headers.common['Authorization'] = `Bearer ${token}`;
          const response = await axios.get('http://localhost:8080/api/auth/me', {
            params: { token }
          });
          setUser(response.data);
          console.log('User loaded:', response.data);
        } catch (error) {
          console.error('Failed to fetch user:', error);
          logout();
        }
      }
      setLoading(false);
    };
    loadUser();
  }, [token]);

  const login = async (email, password) => {
    try {
      const response = await axios.post('http://localhost:8080/api/auth/login', { 
        email, 
        password 
      });
      const { access_token } = response.data;
      setToken(access_token);
      localStorage.setItem('token', access_token);
      axios.defaults.headers.common['Authorization'] = `Bearer ${access_token}`;
      
      // Fetch user data (includes preferred_topics, which determines
      // whether topic selection should be skipped)
      const userResponse = await axios.get('http://localhost:8080/api/auth/me', {
        params: { token: access_token }
      });
      setUser(userResponse.data);
      
      return true;
    } catch (error) {
      console.error('Login error:', error);
      return false;
    }
  };

  const logout = () => {
    console.log('Logging out...');
    setToken('');
    setUser(null);
    localStorage.removeItem('token');
    delete axios.defaults.headers.common['Authorization'];
  };

  const register = async (name, email, password) => {
    try {
      const response = await axios.post('http://localhost:8080/api/auth/register', { 
        name, 
        email, 
        password 
      });
      return response.data;
    } catch (error) {
      console.error('Registration error:', error);
      throw error;
    }
  };

  const updatePreferences = async (preferredTopics) => {
    try {
      const response = await axios.put('http://localhost:8080/api/users/preferences', 
        { preferred_topics: preferredTopics }, 
        {
          params: { token }
        }
      );
      setUser(response.data);
      return response.data;
    } catch (error) {
      console.error('Update preferences error:', error);
      throw error;
    }
  };

  const updateProfile = async (name) => {
    try {
      const response = await axios.put('http://localhost:8080/api/users/profile',
        { name },
        { params: { token } }
      );
      setUser(response.data);
      return response.data;
    } catch (error) {
      console.error('Update profile error:', error);
      throw error;
    }
  };

  const getEmailStatus = async () => {
    try {
      const response = await axios.get('http://localhost:8080/api/notifications/email/status', {
        params: { token }
      });
      return response.data;
    } catch (error) {
      console.error('Get email status error:', error);
      throw error;
    }
  };

  const updateEmailSettings = async ({ emailNotificationsEnabled, emailNotificationSchedule }) => {
    try {
      const payload = {};
      if (emailNotificationsEnabled !== undefined) {
        payload.email_notifications_enabled = emailNotificationsEnabled;
      }
      if (emailNotificationSchedule !== undefined) {
        payload.email_notification_schedule = emailNotificationSchedule;
      }
      const response = await axios.put('http://localhost:8080/api/notifications/email', payload, {
        params: { token }
      });
      setUser(response.data);
      return response.data;
    } catch (error) {
      console.error('Update email settings error:', error);
      throw error;
    }
  };

  const sendEmailTest = async (message) => {
    try {
      const response = await axios.post(
        'http://localhost:8080/api/notifications/email/test',
        message ? { message } : {},
        { params: { token } }
      );
      return response.data;
    } catch (error) {
      console.error('Send email test error:', error);
      throw error;
    }
  };

  const deleteAccount = async (password) => {
    try {
      await axios.delete('http://localhost:8080/api/users/me', {
        data: { password },
        params: { token }
      });
      logout();
      return true;
    } catch (error) {
      console.error('Delete account error:', error);
      throw error;
    }
  };

  const getFeed = async ({ topic, limit } = {}) => {
    try {
      const params = { token };
      if (topic && topic !== 'all') params.topic = topic;
      if (limit) params.limit = limit;
      const response = await axios.get('http://localhost:8080/api/articles/feed', { params });
      return response.data;
    } catch (error) {
      console.error('Get feed error:', error);
      throw error;
    }
  };

  const refreshFeed = async () => {
    try {
      const response = await axios.post('http://localhost:8080/api/articles/refresh', {}, {
        params: { token }
      });
      return response.data;
    } catch (error) {
      console.error('Refresh feed error:', error);
      throw error;
    }
  };

  // Called from the Topic Selection page on first-time setup. Persists to
  // the backend (MongoDB) via updatePreferences so it's remembered for
  // future logins/devices, and topicsCompleted flips automatically since it
  // is derived from user.preferred_topics.
  const completeTopicSelection = async (topics) => {
    console.log('Completing topic selection with topics:', topics);
    return updatePreferences(topics);
  };

  const getSelectedTopics = () => selectedTopics;

  const value = {
    token,
    user,
    loading,
    topicsCompleted,
    selectedTopics,
    login,
    logout,
    register,
    updatePreferences,
    updateProfile,
    completeTopicSelection,
    getSelectedTopics,
    getEmailStatus,
    updateEmailSettings,
    sendEmailTest,
    deleteAccount,
    getFeed,
    refreshFeed
  };

  return (
    <AuthContext.Provider value={value}>
      {!loading && children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  return useContext(AuthContext);
};
