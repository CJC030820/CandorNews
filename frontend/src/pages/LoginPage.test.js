import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import LoginPage from './LoginPage';

// Mock useAuth hook
jest.mock('../context/AuthContext', () => ({
  useAuth: () => ({
    login: jest.fn(),
  }),
}));

test('renders login form with email and password inputs', () => {
  render(
    <MemoryRouter initialEntries={['/login']}>
      <LoginPage />
    </MemoryRouter>
  );

  const emailInput = screen.getByLabelText(/email:/i);
  const passwordInput = screen.getByLabelText(/password:/i);
  const submitButton = screen.getByRole('button', { name: /login/i });

  expect(emailInput).toBeInTheDocument();
  expect(passwordInput).toBeInTheDocument();
  expect(submitButton).toBeInTheDocument();
});

test('calls login function on form submit with correct credentials', async () => {
  // Get the mock login function
  const { useAuth } = require('../context/AuthContext');
  const mockLogin = useAuth().login;
  mockLogin.mockResolvedValueOnce(true); // Resolve to true (successful login)

  render(
    <MemoryRouter initialEntries={['/login']}>
      <LoginPage />
    </MemoryRouter>
  );

  const emailInput = screen.getByLabelText(/email:/i);
  const passwordInput = screen.getByLabelText(/password:/i);
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
  const mockLogin = useAuth().login;
  mockLogin.mockRejectedValueOnce(new Error('Login failed'));

  render(
    <MemoryRouter initialEntries={['/login']}>
      <LoginPage />
    </MemoryRouter>
  );

  const emailInput = screen.getByLabelText(/email:/i);
  const passwordInput = screen.getByLabelText(/password:/i);
  const submitButton = screen.getByRole('button', { name: /login/i });

  fireEvent.change(emailInput, { target: { value: 'test@example.com' } });
  fireEvent.change(passwordInput, { target: { value: 'wrong' } });
  fireEvent.click(submitButton);

  // Wait for error message to appear
  const errorMessage = await screen.findByText(/login failed/i);
  expect(errorMessage).toBeInTheDocument();
});