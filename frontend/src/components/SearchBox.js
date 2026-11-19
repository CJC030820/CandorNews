import React, { useCallback, useEffect, useRef, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import './SearchBox.css';

const DELAY_MS = 150;

// Search box with keyword suggestions. Typing shows words and phrases from
// recent headlines that complete what is typed; an empty box shows trending
// topics. Works with mouse, touch and keyboard (Up/Down, Enter, Escape).
const SearchBox = ({ value, onChange }) => {
  const { user, suggestKeywords } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [items, setItems] = useState([]);
  const [kind, setKind] = useState('completions');
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(-1);
  const inputRef = useRef(null);
  const timer = useRef(null);
  const request = useRef(0);
  const fetchRef = useRef(suggestKeywords);
  fetchRef.current = suggestKeywords;

  const load = useCallback((q) => {
    window.clearTimeout(timer.current);
    if (!user || !fetchRef.current) return;
    const id = ++request.current;
    timer.current = window.setTimeout(async () => {
      try {
        const data = await fetchRef.current(q);
        if (id !== request.current) return;           // a newer request is on its way
        // What the user typed comes first, then words and phrases that complete it.
        const typedRow = data.query ? [{ ...data.query, typed: true }] : [];
        setItems([...typedRow, ...(data.suggestions || [])]);
        setKind(data.kind || 'completions');
        setActive(-1);
      } catch {
        if (id === request.current) setItems([]);
      }
    }, DELAY_MS);
  }, [user]);

  useEffect(() => () => window.clearTimeout(timer.current), []);

  const choose = (text) => {
    onChange(text);
    setOpen(false);
    setItems([]);
    inputRef.current?.blur();                          // closes the phone keyboard
    if (location.pathname !== '/feed') navigate('/feed');
  };

  const onKeyDown = (e) => {
    if (!open || !items.length) {
      if (e.key === 'ArrowDown') { setOpen(true); load(value); }
      return;
    }
    if (e.key === 'ArrowDown') { e.preventDefault(); setActive((a) => (a + 1) % items.length); }
    else if (e.key === 'ArrowUp') { e.preventDefault(); setActive((a) => (a <= 0 ? items.length - 1 : a - 1)); }
    else if (e.key === 'Enter') {
      if (active >= 0) { e.preventDefault(); choose(items[active].text); } else { setOpen(false); }
    } else if (e.key === 'Escape') { setOpen(false); setActive(-1); }
  };

  const typed = value.trim().toLowerCase();
  const label = (text) => {
    if (typed && text.toLowerCase().startsWith(typed)) {
      return <>{text.slice(0, typed.length)}<strong>{text.slice(typed.length)}</strong></>;
    }
    return <strong>{text}</strong>;
  };
  const showList = open && items.length > 0;
  const countText = (n) => (n === 0 ? 'no articles' : `${n} ${n === 1 ? 'article' : 'articles'}`);

  return (
    <div className="search-bar-container search-box">
      <div className="search-bar">
        <input
          ref={inputRef}
          type="text"
          placeholder="Search articles..."
          value={value}
          onChange={(e) => { onChange(e.target.value); setOpen(true); load(e.target.value); }}
          onFocus={() => { setOpen(true); load(value); }}
          onBlur={() => setOpen(false)}
          onKeyDown={onKeyDown}
          className="search-input"
          role="combobox"
          aria-label="Search articles"
          aria-autocomplete="list"
          aria-expanded={showList}
          aria-controls="search-suggestions"
          aria-activedescendant={showList && active >= 0 ? `search-suggestion-${active}` : undefined}
          autoComplete="off"
        />
        {value && (
          <button onClick={() => { onChange(''); load(''); }} className="search-clear" title="Clear search" type="button">
            Clear
          </button>
        )}
      </div>
      {showList && (
        <ul className="search-suggestions" id="search-suggestions" role="listbox"
            aria-label={kind === 'trending' ? 'Trending now' : 'Suggestions'}>
          {kind === 'trending' && <li className="search-suggestions-title" aria-hidden="true">Trending now</li>}
          {items.map((item, i) => (
            <li
              key={item.text}
              id={`search-suggestion-${i}`}
              role="option"
              aria-selected={i === active}
              className={`search-suggestion${i === active ? ' active' : ''}${item.typed ? ' typed' : ''}${item.count === 0 ? ' empty' : ''}`}
              // mousedown keeps the input focused, so the click is not lost to onBlur
              onMouseDown={(e) => { e.preventDefault(); choose(item.text); }}
              onMouseEnter={() => setActive(i)}
            >
              <span className="search-suggestion-text">
                {item.typed ? <>Search &ldquo;{item.text}&rdquo;</> : label(item.text)}
              </span>
              <span className="search-suggestion-count">{countText(item.count)}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
};

export default SearchBox;
