import React from 'react';
import { render } from '@testing-library/react';
import { BookmarkIcon, MoonIcon, RefreshIcon } from './Icons';

test('bookmark icon is an outline when not saved and filled when saved', () => {
  const { container, rerender } = render(<BookmarkIcon />);
  expect(container.querySelector('path').getAttribute('fill')).toBe('none');
  rerender(<BookmarkIcon filled />);
  expect(container.querySelector('path').getAttribute('fill')).toBe('currentColor');
});

test('icons follow the text colour and are hidden from screen readers by default', () => {
  const { container } = render(<><MoonIcon /><RefreshIcon size={18} /></>);
  const [moon, refresh] = container.querySelectorAll('svg');
  expect(moon.getAttribute('aria-hidden')).toBe('true');
  expect(moon.querySelector('path').getAttribute('fill')).toBe('currentColor');
  expect(refresh.getAttribute('width')).toBe('18');
});

test('email icon is an outlined envelope in the text colour', () => {
  const { EmailIcon } = require('./Icons');
  const { container } = render(<EmailIcon />);
  expect(container.querySelector('rect')).not.toBeNull();
  expect(container.querySelector('g').getAttribute('stroke')).toBe('currentColor');
});

test('share and back icons render in the text colour', () => {
  const { ShareIcon, BackIcon } = require('./Icons');
  const { container } = render(<><ShareIcon /><BackIcon /></>);
  const [share, back] = container.querySelectorAll('svg');
  expect(share.querySelector('path').getAttribute('fill')).toBe('currentColor');
  expect(back.querySelector('path').getAttribute('stroke')).toBe('currentColor');
});
