import { combineStories } from './stories';

const a = (id, storyId, source, trustScore, rawDate) => ({ id, storyId, source, trustScore, rawDate });

test('shows one card per story, with the best-scored version first', () => {
  const cards = combineStories([
    a('1', 's1', 'New Straits Times', 70, '2026-11-20T09:00:00Z'),
    a('2', 's1', 'Bernama', 82, '2026-11-20T08:00:00Z'),
    a('3', 's2', 'Free Malaysia Today', 60, '2026-11-20T07:00:00Z'),
  ]);
  expect(cards.map((c) => c.id)).toEqual(['2', '3']);
  expect(cards[0].otherVersions).toEqual([{ id: '1', source: 'New Straits Times', trustScore: 70 }]);
  expect(cards[0].versionIds).toEqual(['1', '2']);
  expect(cards[1].otherVersions).toBeUndefined();
});

test('ties go to the version published first; articles without a story stay single', () => {
  const cards = combineStories([
    a('1', 's1', 'NST', 75, '2026-11-20T09:00:00Z'),
    a('2', 's1', 'Bernama', 75, '2026-11-20T08:00:00Z'),
    { id: '9', source: 'FMT', trustScore: 50, rawDate: '2026-11-20T10:00:00Z' },
  ]);
  expect(cards.map((c) => c.id)).toEqual(['2', '9']);
});

test('a search match still names every followed version of its story', () => {
  const pool = [a('1', 's1', 'NST', 70, '2026-11-20T09:00:00Z'), a('2', 's1', 'Bernama', 82, '2026-11-20T08:00:00Z')];
  const cards = combineStories([pool[0]], pool);
  expect(cards).toHaveLength(1);
  expect(cards[0].id).toBe('1');
  expect(cards[0].otherVersions.map((v) => v.source)).toEqual(['Bernama']);
});

test('a developing story shows one card: its latest update, with the number of updates', () => {
  const t = (id, storyId, source, trustScore, rawDate) => ({ id, storyId, threadId: 'thread', source, trustScore, rawDate });
  const cards = combineStories([
    t('1', 'found', 'NST', 80, '2026-11-18T12:30:00Z'),
    t('2', 'probe', 'NST', 70, '2026-11-18T15:24:00Z'),
    t('3', 'probe', 'FMT', 75, '2026-11-18T15:56:00Z'),
    { id: '9', source: 'Bernama', trustScore: 60, rawDate: '2026-11-18T14:00:00Z' },
  ]);
  expect(cards.map((c) => c.id)).toEqual(['3', '9']);
  expect(cards[0].updateCount).toBe(2);
  expect(cards[0].otherVersions.map((v) => v.source)).toEqual(['NST']);
  expect(cards[0].versionIds).toEqual(['1', '2', '3']);
});
