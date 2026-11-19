import React from 'react';
import { EMPTY_FILTERS, TIME_OPTIONS } from '../utils/historyFilter';
import './ArticleFilters.css';

// Keyword, time and category filters for History and Bookmarks.
const ArticleFilters = ({ value, onChange, categories = [], total, shown, timeLabel = 'Time', label = 'Filter articles' }) => {
  const set = (key) => (e) => onChange({ ...value, [key]: e.target.value });
  const filtering = value.query.trim() !== '' || value.time !== 'all' || value.category !== 'all';
  return (
    <div className="article-filters" role="search" aria-label={label}>
      <input
        type="search"
        className="article-filter-search"
        placeholder="Search headline or publisher..."
        value={value.query}
        onChange={set('query')}
        aria-label="Search by keyword"
      />
      <select className="article-filter-select" value={value.time} onChange={set('time')} aria-label={timeLabel}>
        {TIME_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
      </select>
      {value.time === 'date' && (
        <input
          type="date"
          className="article-filter-date"
          value={value.date}
          max={new Date().toISOString().slice(0, 10)}
          onChange={set('date')}
          aria-label={`${timeLabel} date`}
        />
      )}
      <select className="article-filter-select" value={value.category} onChange={set('category')} aria-label="Category">
        <option value="all">All categories</option>
        {categories.map((c) => <option key={c} value={c}>{c}</option>)}
      </select>
      {filtering && (
        <button type="button" className="article-filter-clear" onClick={() => onChange(EMPTY_FILTERS)}>
          Clear filters
        </button>
      )}
      <p className="article-filter-count" aria-live="polite">Showing {shown} of {total}</p>
    </div>
  );
};

export default ArticleFilters;
