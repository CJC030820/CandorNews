import React from 'react';
import { Link } from 'react-router-dom';
import './StoryTimeline.css';

const when = (value) => {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return { day: '', time: value || '' };
  return {
    day: date.toLocaleDateString([], { weekday: 'short', day: 'numeric', month: 'short' }),
    time: date.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' }),
  };
};

// How a developing story unfolded: one entry per update, oldest first.
export default function StoryTimeline({ timeline }) {
  if (!timeline || timeline.length < 2) return null;
  return (
    <section className="story-timeline" aria-labelledby="timeline">
      <h2 id="timeline">Story timeline</h2>
      <p className="story-timeline-intro">
        This story developed over {timeline.length} updates. Each entry is one update, with the publishers that reported it.
      </p>
      <ol>
        {timeline.map((entry, index) => {
          const { day, time } = when(entry.date);
          const latest = index === timeline.length - 1;
          return (
            <li key={entry.storyId} className={entry.current ? 'current' : ''}>
              <span className="story-timeline-dot" aria-hidden="true" />
              <p className="story-timeline-when">
                <time dateTime={entry.date}>{day} · {time}</time>
                {latest && <span className="story-timeline-tag">Latest</span>}
                {entry.current && <span className="story-timeline-tag current">You are reading this</span>}
              </p>
              {entry.current
                ? <p className="story-timeline-title">{entry.title}</p>
                : <Link className="story-timeline-title" to={`/article/${entry.id}`}>{entry.title}</Link>}
              <p className="story-timeline-sources">{entry.sources.join(' · ')}</p>
            </li>
          );
        })}
      </ol>
    </section>
  );
}
