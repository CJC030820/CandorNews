import React from 'react';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import StoryTimeline from './StoryTimeline';

const timeline = [
  { storyId: 'a', id: 'a1', title: 'Student found dead at boarding school', date: '2026-11-18T12:30:00Z', sources: ['New Straits Times'], current: false },
  { storyId: 'b', id: 'b1', title: 'PM orders immediate probe', date: '2026-11-18T15:24:00Z', sources: ['New Straits Times', 'Free Malaysia Today'], current: true },
  { storyId: 'c', id: 'c1', title: 'Police confirm cause of death', date: '2026-11-19T08:30:00Z', sources: ['Bernama'], current: false },
];

test('lists each update oldest first, linking to the other updates', () => {
  render(<MemoryRouter><StoryTimeline timeline={timeline} /></MemoryRouter>);
  expect(screen.getByRole('heading', { name: 'Story timeline' })).toBeInTheDocument();
  expect(screen.getByText(/developed over 3 updates/)).toBeInTheDocument();
  const items = screen.getAllByRole('listitem');
  expect(items[0]).toHaveTextContent('Student found dead');
  expect(items[2]).toHaveTextContent('Latest');
  expect(items[1]).toHaveTextContent('You are reading this');
  expect(screen.getByRole('link', { name: 'Police confirm cause of death' })).toHaveAttribute('href', '/article/c1');
  expect(screen.queryByRole('link', { name: 'PM orders immediate probe' })).not.toBeInTheDocument();
  expect(screen.getByText('New Straits Times · Free Malaysia Today')).toBeInTheDocument();
});

test('shows nothing for a story without updates', () => {
  const { container } = render(<MemoryRouter><StoryTimeline timeline={[timeline[0]]} /></MemoryRouter>);
  expect(container).toBeEmptyDOMElement();
});
