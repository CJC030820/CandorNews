import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import ShareMenu from './ShareMenu';

const article = {
  id: 'abc123', title: 'Parliament passes budget',
  description: 'A long summary that must not be shared.',
  url: 'https://www.nst.com.my/original-story',
};
const siteLink = `${window.location.origin}/article/abc123`;

afterEach(() => { delete navigator.share; });

test('phone share sheet gets only the headline and the CandorNews link', async () => {
  navigator.share = jest.fn().mockResolvedValue(undefined);
  render(<ShareMenu article={article} />);
  fireEvent.click(screen.getByRole('button', { name: 'Share this article' }));
  await waitFor(() => expect(navigator.share).toHaveBeenCalledWith({
    title: 'Parliament passes budget', text: 'Parliament passes budget', url: siteLink,
  }));
});

test('desktop menu shares only title and CandorNews link, never the original source', async () => {
  const open = jest.spyOn(window, 'open').mockImplementation(() => null);
  Object.assign(navigator, { clipboard: { writeText: jest.fn().mockResolvedValue(undefined) } });
  render(<ShareMenu article={article} />);
  fireEvent.click(screen.getByRole('button', { name: 'Share this article' }));
  expect(screen.queryByText(/original/i)).toBeNull();
  fireEvent.click(screen.getByText('Copy title and link'));
  await waitFor(() => expect(navigator.clipboard.writeText).toHaveBeenCalledWith(`Parliament passes budget\n${siteLink}`));
  fireEvent.click(screen.getByText('Email'));
  const mailto = decodeURIComponent(open.mock.calls[0][0]);
  expect(mailto).toContain('subject=Parliament passes budget');
  expect(mailto).toContain(`body=Parliament passes budget\n${siteLink}`);
  expect(mailto).not.toContain('long summary');
  expect(mailto).not.toContain('nst.com.my');
  open.mockRestore();
});
