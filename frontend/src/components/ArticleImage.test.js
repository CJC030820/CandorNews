import React from 'react';
import { render, fireEvent, screen } from '@testing-library/react';
import ArticleImage, { publisherName } from './ArticleImage';

const base = { id: '7', title: 'Story', source: 'BERNAMA - English Version', categories: ['Politics'],
  image: 'https://www.bernama.com/storage/photos/x-medium' };
const stored = 'http://localhost:8080/api/articles/7/image';
const img = (c) => c.querySelector('img');

test('uses the stored copy first when the server has one', () => {
  const { container } = render(<ArticleImage article={{ ...base, imageStored: true }} />);
  expect(img(container).getAttribute('src')).toBe(stored);
  fireEvent.error(img(container));
  expect(img(container).getAttribute('src')).toBe(base.image);
});

test('tries the publisher image first when no stored copy exists, then the stored copy', () => {
  const { container } = render(<ArticleImage article={base} />);
  expect(img(container).getAttribute('src')).toBe(base.image);
  fireEvent.error(img(container));
  expect(img(container).getAttribute('src')).toBe(stored);
});

test('shows a publisher placeholder instead of a broken image', () => {
  const { container } = render(<ArticleImage article={base} />);
  fireEvent.error(img(container));
  fireEvent.error(img(container));
  expect(img(container)).toBeNull();
  expect(screen.getByRole('img', { name: 'Bernama news' })).toBeInTheDocument();
  expect(screen.getByText('Politics')).toBeInTheDocument();
});

test('articles saved without an image still show the placeholder', () => {
  render(<ArticleImage article={{ id: '8', title: 'No picture', source: 'Business – Free Malaysia Today (FMT)' }} />);
  expect(screen.getByRole('img', { name: 'Free Malaysia Today news' })).toBeInTheDocument();
});

test('publisher names are shortened', () => {
  expect(publisherName('New Straits Times')).toBe('New Straits Times');
  expect(publisherName('World – Free Malaysia Today (FMT)')).toBe('Free Malaysia Today');
  expect(publisherName('')).toBe('CandorNews');
});
