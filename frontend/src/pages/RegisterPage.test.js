import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import RegisterPage from './RegisterPage';

// Mock useAuth hook
jest.mock('../context/AuthContext', () => ({
  useAuth: () => ({
    register: jest.fn(),
  }),
}));

test('renders register form with name, email, password inputs', () => {
  render(
    <MemoryRouter initialEntries={['/register']}>
      <RegisterPage />
    </MemoryRouter>
  );

  const nameInput = screen.getByLabelText(/name:/i);
  const emailInput = screen.getByLabelText(/email:/i);
  const passwordInput = screen.getByLabelText(/password:/i);
  const submitButton = screen.getByRole('button', { name: /register/i });

  expect(nameInput).toBeInTheDocument();
  expect(emailInput).toBeInTheDocument();
  expect(passwordInput).toBeInTheDocument();
  expect(submitButton).toBeInTheDocument();
});

test('calls register function on form submit with correct data', async () => {
  const { useAuth } = require('../context/AuthContext');
  const mockRegister = useAuth().register;
  mockRegister.mockResolvedValueOnce({}); // Resolve with empty object

  render(
    <MemoryRouter initialEntries={['/register']}>
      <RegisterPage />
    </MemoryRouter>
  );

  const nameInput = screen.getByLabelText(/name:/i);
  const emailInput = screen.getByLabelText(/email:/i);
  const passwordInput = screen.getByLabelText(/password:/i);
  const submitButton = screen.getByRole('button', { name: /register/i });

  fireEvent.change(nameInput, { target: { value: 'Test User' } });
  fireEvent.change(emailInput, { target: { value: 'test@example.com' } });
  fireEvent.change(passwordInput, { target: { value: 'password123' } });

  fireEvent.click(submitButton);

  await waitFor(() => {
    expect(mockRegister).toHaveBeenCalledWith('Test User', 'test@example.com', 'password123');
  });
});

test('shows error message when registration fails', async () => {
  const { useAuth } = require('../context/AuthContext');
  const mockRegister = useAuth().register;
  mockRegister.mockRejectedValueOnce(new Error('Registration failed'));

  render(
    <MemoryRouter initialEntries={['/register']}>
      <RegisterPage />
    </MemoryRouter>
  );

  const nameInput = screen.getByLabelText(/name:/i);
  const emailInput = screen.getByLabelText(/email:/i);
  const passwordInput = screen.getByLabelText(/password:/i);
  const submitButton = screen.getByRole('button', { name: /register/i });

  fireEvent.change(nameInput, { target: { value: 'Test User' } });
  fireEvent.change(emailInput, { target: { value: 'test@example.com' } });
  fireEvent.change(passwordInput, { target: { value: 'wrong' } });
  fireEvent.click(submitButton);

  const errorMessage = await screen.findByText(/registration failed/i);
  expect(errorMessage).toBeInTheDocument();
});