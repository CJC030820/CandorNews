import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import LoginPage from './LoginPage';

const mockAction = jest.fn();

// Mock useAuth hook
jest.mock('../context/AuthContext', () => ({
  useAuth: () => ({
    login: (...args) => mockAction(...args),
  }),
}));

beforeEach(() => mockAction.mockReset());

test('renders login form with email and password inputs', () => {
  render(
    <MemoryRouter initialEntries={['/login']}>
      <LoginPage />
    </MemoryRouter>
  );

  const emailInput = screen.getByLabelText(/email address/i);
  const passwordInput = screen.getByLabelText(/^password$/i);
  const submitButton = screen.getByRole('button', { name: /login/i });

  expect(emailInput).toBeInTheDocument();
  expect(passwordInput).toBeInTheDocument();
  expect(submitButton).toBeInTheDocument();
});

test('calls login function on form submit with correct credentials', async () => {
  // Get the mock login function
  const { useAuth } = require('../context/AuthContext');
  const mockLogin = mockAction;
  mockLogin.mockResolvedValueOnce(true); // Resolve to true (successful login)

  render(
    <MemoryRouter initialEntries={['/login']}>
      <LoginPage />
    </MemoryRouter>
  );

  const emailInput = screen.getByLabelText(/email address/i);
  const passwordInput = screen.getByLabelText(/^password$/i);
  const submitButton = screen.getByRole('button', { name: /login/i });

  // Fill in the form
  fireEvent.change(emailInput, { target: { value: 'test@example.com' } });
  fireEvent.change(passwordInput, { target: { value: 'password123' } });

  // Submit the form
  fireEvent.click(submitButton);

  // Wait for login to be called
  await waitFor(() => {
    expect(mockLogin).toHaveBeenCalledWith('test@example.com', 'password123');
  });
});

test('shows error message when login fails', async () => {
  const { useAuth } = require('../context/AuthContext');
  const mockLogin = mockAction;
  mockLogin.mockRejectedValueOnce(new Error('Login failed'));

  render(
    <MemoryRouter initialEntries={['/login']}>
      <LoginPage />
    </MemoryRouter>
  );

  const emailInput = screen.getByLabelText(/email address/i);
  const passwordInput = screen.getByLabelText(/^password$/i);
  const submitButton = screen.getByRole('button', { name: /login/i });

  fireEvent.change(emailInput, { target: { value: 'test@example.com' } });
  fireEvent.change(passwordInput, { target: { value: 'wrong' } });
  fireEvent.click(submitButton);

  // Wait for error message to appear
  const errorMessage = await screen.findByText(/login failed/i);
  expect(errorMessage).toBeInTheDocument();
});
const loginAndLand = async () => {
  mockAction.mockResolvedValueOnce(true);
  render(
    <MemoryRouter initialEntries={['/login']}>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/feed" element={<p>Feed page</p>} />
        <Route path="/article/:id" element={<p>Article page</p>} />
      </Routes>
    </MemoryRouter>
  );
  fireEvent.change(screen.getByLabelText(/email address/i), { target: { value: 'reader@example.com' } });
  fireEvent.change(screen.getByLabelText(/^password$/i), { target: { value: 'Test-password-123' } });
  fireEvent.click(screen.getByRole('button', { name: /login/i }));
};

test('after login, returns to the article that was opened from a link', async () => {
  sessionStorage.setItem('returnAfterLogin', '/article/abc123');
  await loginAndLand();
  expect(await screen.findByText('Article page')).toBeInTheDocument();
  expect(sessionStorage.getItem('returnAfterLogin')).toBeNull();
});

test('after login without a saved article, goes to the feed', async () => {
  sessionStorage.removeItem('returnAfterLogin');
  await loginAndLand();
  expect(await screen.findByText('Feed page')).toBeInTheDocument();
});

test('ignores saved paths that are not article pages', async () => {
  sessionStorage.setItem('returnAfterLogin', 'https://evil.example/phish');
  await loginAndLand();
  expect(await screen.findByText('Feed page')).toBeInTheDocument();
});

test('the email is filled in when coming from "Log in instead"', () => {
  render(<MemoryRouter initialEntries={[{ pathname: '/login', state: { email: 'taken@example.com' } }]}><LoginPage /></MemoryRouter>);
  expect(screen.getByLabelText(/email address/i)).toHaveValue('taken@example.com');
});

test('after registering, the login page confirms the account was created', () => {
  render(<MemoryRouter initialEntries={[{ pathname: '/login', state: { email: 'new@example.com', registered: true } }]}><LoginPage /></MemoryRouter>);
  expect(screen.getByRole('status')).toHaveTextContent('Your account has been created');
  expect(screen.getByLabelText(/email address/i)).toHaveValue('new@example.com');
});
