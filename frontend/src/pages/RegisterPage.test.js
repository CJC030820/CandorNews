import React from 'react';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import RegisterPage from './RegisterPage';

const mockAction = jest.fn();

// Mock useAuth hook
jest.mock('../context/AuthContext', () => ({
  useAuth: () => ({
    register: (...args) => mockAction(...args),
  }),
}));

beforeEach(() => mockAction.mockReset());

test('renders register form with name, email, password inputs', () => {
  render(
    <MemoryRouter initialEntries={['/register']}>
      <RegisterPage />
    </MemoryRouter>
  );

  const nameInput = screen.getByLabelText(/full name/i);
  const emailInput = screen.getByLabelText(/email address/i);
  const passwordInput = screen.getByLabelText(/^password$/i);
  const submitButton = screen.getByRole('button', { name: /register/i });

  expect(nameInput).toBeInTheDocument();
  expect(emailInput).toBeInTheDocument();
  expect(passwordInput).toBeInTheDocument();
  expect(submitButton).toBeInTheDocument();
});

test('calls register function on form submit with correct data', async () => {
  const { useAuth } = require('../context/AuthContext');
  const mockRegister = mockAction;
  mockRegister.mockResolvedValueOnce({}); // Resolve with empty object

  render(
    <MemoryRouter initialEntries={['/register']}>
      <RegisterPage />
    </MemoryRouter>
  );

  const nameInput = screen.getByLabelText(/full name/i);
  const emailInput = screen.getByLabelText(/email address/i);
  const passwordInput = screen.getByLabelText(/^password$/i);
  const submitButton = screen.getByRole('button', { name: /register/i });

  fireEvent.change(nameInput, { target: { value: 'Test User' } });
  fireEvent.change(emailInput, { target: { value: 'test@example.com' } });
  fireEvent.change(passwordInput, { target: { value: 'password123' } });

  fireEvent.change(screen.getByLabelText(/confirm password/i), {target: {value: passwordInput.value}});
  fireEvent.click(submitButton);

  await waitFor(() => {
    expect(mockRegister).toHaveBeenCalledWith('Test User', 'test@example.com', 'password123');
  });
});

test('shows error message when registration fails', async () => {
  const { useAuth } = require('../context/AuthContext');
  const mockRegister = mockAction;
  mockRegister.mockRejectedValueOnce(Object.assign(new Error('Registration failed'), { response: { status: 500, data: {} } }));

  render(
    <MemoryRouter initialEntries={['/register']}>
      <RegisterPage />
    </MemoryRouter>
  );

  const nameInput = screen.getByLabelText(/full name/i);
  const emailInput = screen.getByLabelText(/email address/i);
  const passwordInput = screen.getByLabelText(/^password$/i);
  const submitButton = screen.getByRole('button', { name: /register/i });

  fireEvent.change(nameInput, { target: { value: 'Test User' } });
  fireEvent.change(emailInput, { target: { value: 'test@example.com' } });
  fireEvent.change(passwordInput, { target: { value: 'password123' } });
  fireEvent.change(screen.getByLabelText(/confirm password/i), {target: {value: passwordInput.value}});
  fireEvent.click(submitButton);

  const errorMessage = await screen.findByText(/registration failed/i);
  expect(errorMessage).toBeInTheDocument();
});
const fill = (email = 'taken@example.com') => {
  fireEvent.change(screen.getByLabelText(/full name/i), { target: { value: 'Reader', name: 'name' } });
  fireEvent.change(screen.getByLabelText(/email address/i), { target: { value: email, name: 'email' } });
  fireEvent.change(screen.getByLabelText(/^password$/i), { target: { value: 'Password123', name: 'password' } });
  fireEvent.change(screen.getByLabelText(/confirm password/i), { target: { value: 'Password123', name: 'confirmPassword' } });
  fireEvent.click(screen.getByRole('button', { name: /register/i }));
};
const serverError = (status, detail) => Object.assign(new Error('Request failed'), { response: { status, data: { detail } } });

test('an email that is already registered shows a warning with a login link that keeps the email', async () => {
  const { Routes, Route, useLocation } = require('react-router-dom');
  const LoginProbe = () => <p>Login page for {useLocation().state?.email}</p>;
  mockAction.mockRejectedValueOnce(serverError(400, 'Email already registered'));
  render(
    <MemoryRouter initialEntries={['/register']}>
      <Routes>
        <Route path="/register" element={<RegisterPage />} />
        <Route path="/login" element={<LoginProbe />} />
      </Routes>
    </MemoryRouter>
  );
  fill();
  const warning = await screen.findByRole('alert');
  expect(warning).toHaveClass('register-warning');
  expect(warning).toHaveTextContent('This email is already registered.');
  expect(warning).toHaveTextContent('taken@example.com');
  fireEvent.click(screen.getByRole('link', { name: 'Log in instead' }));
  expect(screen.getByText('Login page for taken@example.com')).toBeInTheDocument();
});

test('editing the email removes the warning', async () => {
  mockAction.mockRejectedValueOnce(serverError(400, 'Email already registered'));
  render(<MemoryRouter><RegisterPage /></MemoryRouter>);
  fill();
  await screen.findByText('This email is already registered.');
  fireEvent.change(screen.getByLabelText(/email address/i), { target: { value: 'new@example.com', name: 'email' } });
  expect(screen.queryByText('This email is already registered.')).not.toBeInTheDocument();
});

test('other failures get their own message', async () => {
  mockAction.mockRejectedValueOnce(serverError(422, [{ msg: 'invalid' }]));
  const { unmount } = render(<MemoryRouter><RegisterPage /></MemoryRouter>);
  fill();
  expect(await screen.findByText(/Please check your details/)).toBeInTheDocument();
  unmount();
  mockAction.mockRejectedValueOnce(new Error('Network Error'));
  render(<MemoryRouter><RegisterPage /></MemoryRouter>);
  fill();
  expect(await screen.findByText(/Could not reach the server/)).toBeInTheDocument();
});

test('a successful registration says so, then opens the login page with the email', async () => {
  jest.useFakeTimers();
  const { Routes, Route, useLocation } = require('react-router-dom');
  const LoginProbe = () => { const s = useLocation().state; return <p>Login page for {s?.email} registered={String(s?.registered)}</p>; };
  mockAction.mockResolvedValueOnce({ id: 'u1' });
  render(
    <MemoryRouter initialEntries={['/register']}>
      <Routes>
        <Route path="/register" element={<RegisterPage />} />
        <Route path="/login" element={<LoginProbe />} />
      </Routes>
    </MemoryRouter>
  );
  fill('new@example.com');
  expect(await screen.findByText('Registration successful!')).toBeInTheDocument();
  expect(screen.getByRole('button', { name: /register/i })).toBeDisabled();
  act(() => { jest.advanceTimersByTime(1500); });
  expect(screen.getByText('Login page for new@example.com registered=true')).toBeInTheDocument();
  jest.useRealTimers();
});
