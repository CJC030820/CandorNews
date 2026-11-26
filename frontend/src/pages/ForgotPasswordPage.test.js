import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter, Routes, Route, useLocation } from 'react-router-dom';
import ForgotPasswordPage from './ForgotPasswordPage';

const mockRequest = jest.fn();
const mockConfirm = jest.fn();
jest.mock('../context/AuthContext', () => ({
  useAuth: () => ({
    requestPasswordReset: (...a) => mockRequest(...a),
    confirmPasswordReset: (...a) => mockConfirm(...a),
  }),
}));

function LoginStub() {
  const { state } = useLocation();
  return <p>login page {state?.email} {state?.passwordReset ? 'reset' : ''}</p>;
}

const renderPage = () => render(
  <MemoryRouter initialEntries={['/forgot-password']}>
    <Routes>
      <Route path="/forgot-password" element={<ForgotPasswordPage />} />
      <Route path="/login" element={<LoginStub />} />
    </Routes>
  </MemoryRouter>
);

beforeEach(() => { mockRequest.mockReset(); mockConfirm.mockReset(); });

async function sendCode() {
  mockRequest.mockResolvedValueOnce({ detail: 'If an account exists for this email, we have sent a 6-digit code to it.' });
  fireEvent.change(screen.getByLabelText(/email address/i), { target: { value: 'a@example.com' } });
  fireEvent.click(screen.getByRole('button', { name: /send code/i }));
  await screen.findByLabelText(/6-digit code/i);
}

test('sends a code, then sets the new password and returns to login', async () => {
  renderPage();
  await sendCode();
  expect(mockRequest).toHaveBeenCalledWith('a@example.com');
  expect(screen.getByText(/we have sent a 6-digit code/i)).toBeInTheDocument();
  mockConfirm.mockResolvedValueOnce({ status: 'ok' });
  fireEvent.change(screen.getByLabelText(/6-digit code/i), { target: { value: '123456' } });
  fireEvent.change(screen.getByLabelText(/^new password$/i), { target: { value: 'New-password-1' } });
  fireEvent.change(screen.getByLabelText(/confirm new password/i), { target: { value: 'New-password-1' } });
  fireEvent.click(screen.getByRole('button', { name: /change password/i }));
  await screen.findByText(/login page a@example.com reset/);
  expect(mockConfirm).toHaveBeenCalledWith('a@example.com', '123456', 'New-password-1');
});

test('checks the code and passwords before sending', async () => {
  renderPage();
  await sendCode();
  fireEvent.change(screen.getByLabelText(/6-digit code/i), { target: { value: '12ab3' } });
  fireEvent.click(screen.getByRole('button', { name: /change password/i }));
  expect(screen.getByRole('alert')).toHaveTextContent(/6-digit code/);
  fireEvent.change(screen.getByLabelText(/6-digit code/i), { target: { value: '123456' } });
  fireEvent.change(screen.getByLabelText(/^new password$/i), { target: { value: 'New-password-1' } });
  fireEvent.change(screen.getByLabelText(/confirm new password/i), { target: { value: 'Different-1' } });
  fireEvent.click(screen.getByRole('button', { name: /change password/i }));
  expect(screen.getByRole('alert')).toHaveTextContent(/do not match/);
  expect(mockConfirm).not.toHaveBeenCalled();
});

test('shows the server message for a wrong code, and waits before resending', async () => {
  renderPage();
  await sendCode();
  expect(screen.getByRole('button', { name: /send a new code in/i })).toBeDisabled();
  mockConfirm.mockRejectedValueOnce({ response: { status: 400, data: { detail: 'Incorrect code. Please check the email and try again.' } } });
  fireEvent.change(screen.getByLabelText(/6-digit code/i), { target: { value: '000000' } });
  fireEvent.change(screen.getByLabelText(/^new password$/i), { target: { value: 'New-password-1' } });
  fireEvent.change(screen.getByLabelText(/confirm new password/i), { target: { value: 'New-password-1' } });
  fireEvent.click(screen.getByRole('button', { name: /change password/i }));
  await waitFor(() => expect(screen.getByRole('alert')).toHaveTextContent(/incorrect code/i));
});
