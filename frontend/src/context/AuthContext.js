import React, { createContext, useContext, useState, useEffect } from 'react';
import axios from 'axios';

const AuthContext = createContext();

export const AuthProvider = ({ children }) => {
  const [token, setToken] = useState(localStorage.getItem('token') || '');
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const loadUser = async () => {
      if (token) {
        try {
          const response = await axios.get('/api/auth/me', {
            headers: { Authorization: `Bearer ${token}` }
          });
          setUser(response.data);
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
      const response = await axios.post('/api/auth/login', { email, password });
      const { access_token } = response.data;
      setToken(access_token);
      localStorage.setItem('token', access_token);
      // Fetch user data
      const userResponse = await axios.get('/api/auth/me', {
        headers: { Authorization: `Bearer ${access_token}` }
      });
      setUser(userResponse.data);
      return true;
    } catch (error) {
      console.error('Login error:', error);
      return false;
    }
  };

  const logout = () => {
    setToken('');
    setUser(null);
    localStorage.removeItem('token');
  };

  const register = async (name, email, password) => {
    try {
      const response = await axios.post('/api/auth/register', { name, email, password });
      return response.data;
    } catch (error) {
      console.error('Registration error:', error);
      throw error;
    }
  };

  const updatePreferences = async (preferredTopics) => {
    try {
      const response = await axios.put('/api/users/preferences', { preferred_topics: preferredTopics }, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setUser(response.data);
      return response.data;
    } catch (error) {
      console.error('Update preferences error:', error);
      throw error;
    }
  };

  const value = {
    token,
    user,
    loading,
    login,
    logout,
    register,
    updatePreferences
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