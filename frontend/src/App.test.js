import React from 'react';
import { render } from '@testing-library/react';
import App from './App';

// Mock AuthContext
const AuthContext = React.createContext({
  token: '',
  user: null,
  loading: false,
  login: jest.fn(),
  logout: jest.fn(),
  register: jest.fn(),
  updatePreferences: jest.fn()
});

test('renders app without crashing', () => {
  const Wrapper = ({ children }) => (
    <AuthContext.Provider value={{
      token: '',
      user: null,
      loading: false,
      login: jest.fn(),
      logout: jest.fn(),
      register: jest.fn(),
      updatePreferences: jest.fn()
    }}>
      {children}
    </AuthContext.Provider>
  );

  const { container } = render(<Wrapper><App /></Wrapper>);
  expect(container).toBeInTheDocument();
});