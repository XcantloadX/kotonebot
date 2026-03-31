import React from 'react';
import { InputGroup } from '@blueprintjs/core';

export interface AutoCompleteInputProps {
  value: string;
  onChange: (value: string) => void;
  onConfirm?: (value: string) => void;
  suggestions: string[];
  readOnly?: boolean;
  fill?: boolean;
  placeholder?: string;
}

/**
 * Performs fuzzy matching: returns true if every character in `query`
 * appears in `text` in order (case-insensitive).
 */
function fuzzyMatch(text: string, query: string): boolean {
  if (!query) return true;
  const lowerText = text.toLowerCase();
  const lowerQuery = query.toLowerCase();
  let ti = 0;
  for (let qi = 0; qi < lowerQuery.length; qi++) {
    const idx = lowerText.indexOf(lowerQuery[qi], ti);
    if (idx === -1) return false;
    ti = idx + 1;
  }
  return true;
}

/**
 * Scores a fuzzy match — contiguous matches score highest, then earlier positions,
 * then how close together the matched characters are.
 */
function fuzzyScore(text: string, query: string): number {
  if (!query) return 0;
  const lowerText = text.toLowerCase();
  const lowerQuery = query.toLowerCase();
  // Contiguous match bonus: highest score
  if (lowerText.includes(lowerQuery)) {
    return 2000 - lowerText.indexOf(lowerQuery);
  }
  // Non-contiguous: score based on span of matched characters (smaller span = higher score)
  let ti = 0;
  let firstIdx = -1;
  let lastIdx = -1;
  for (let qi = 0; qi < lowerQuery.length; qi++) {
    const idx = lowerText.indexOf(lowerQuery[qi], ti);
    if (idx === -1) return 0;
    if (firstIdx === -1) firstIdx = idx;
    lastIdx = idx;
    ti = idx + 1;
  }
  const span = lastIdx - firstIdx + 1;
  return 1000 - span - firstIdx;
}

const MAX_SUGGESTIONS = 20;

export const AutoCompleteInput: React.FC<AutoCompleteInputProps> = ({
  value,
  onChange,
  onConfirm,
  suggestions,
  readOnly,
  fill,
  placeholder,
}) => {
  const [open, setOpen] = React.useState(false);
  const [activeIndex, setActiveIndex] = React.useState(-1);
  const containerRef = React.useRef<HTMLDivElement>(null);
  const listRef = React.useRef<HTMLUListElement>(null);

  const filtered = React.useMemo(() => {
    if (!value) return [];
    return suggestions
      .filter((s) => fuzzyMatch(s, value) && s !== value)
      .sort((a, b) => fuzzyScore(b, value) - fuzzyScore(a, value))
      .slice(0, MAX_SUGGESTIONS);
  }, [value, suggestions]);

  const shouldShowDropdown = open && filtered.length > 0;

  // Close when clicking outside
  React.useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpen(false);
        setActiveIndex(-1);
      }
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  // Scroll active item into view
  React.useEffect(() => {
    if (activeIndex >= 0 && listRef.current) {
      const item = listRef.current.children[activeIndex] as HTMLElement | undefined;
      item?.scrollIntoView({ block: 'nearest' });
    }
  }, [activeIndex]);

  const handleSelect = (suggestion: string) => {
    onChange(suggestion);
    setOpen(false);
    setActiveIndex(-1);
    onConfirm?.(suggestion);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (!shouldShowDropdown) {
      if (e.key === 'Enter') {
        onConfirm?.(value);
      }
      return;
    }
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setActiveIndex((i) => Math.min(i + 1, filtered.length - 1));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setActiveIndex((i) => Math.max(i - 1, -1));
    } else if (e.key === 'Enter') {
      if (activeIndex >= 0) {
        e.preventDefault();
        handleSelect(filtered[activeIndex]);
      } else {
        onConfirm?.(value);
      }
    } else if (e.key === 'Escape') {
      setOpen(false);
      setActiveIndex(-1);
    }
  };

  return (
    <div ref={containerRef} style={{ position: 'relative', ...(fill ? { flex: 1, minWidth: 0 } : {}) }}>
      <InputGroup
        value={value}
        readOnly={readOnly}
        fill={fill}
        placeholder={placeholder}
        onChange={(e) => {
          onChange(e.target.value);
          setOpen(true);
          setActiveIndex(-1);
        }}
        onFocus={() => setOpen(true)}
        onKeyDown={handleKeyDown}
      />
      {shouldShowDropdown && (
        <ul
          ref={listRef}
          style={{
            position: 'absolute',
            top: '100%',
            left: 0,
            right: 0,
            zIndex: 1000,
            margin: 0,
            padding: '4px 0',
            listStyle: 'none',
            background: '#2f3b46',
            border: '1px solid #394b59',
            borderRadius: 3,
            boxShadow: '0 4px 16px rgba(0,0,0,0.4)',
            maxHeight: 240,
            overflowY: 'auto',
          }}
        >
          {filtered.map((suggestion, i) => (
            <li
              key={suggestion}
              onMouseDown={(e) => {
                e.preventDefault(); // prevent input blur
                handleSelect(suggestion);
              }}
              onMouseEnter={() => setActiveIndex(i)}
              style={{
                padding: '5px 10px',
                cursor: 'pointer',
                fontSize: 12,
                fontFamily: 'monospace',
                color: i === activeIndex ? '#ffffff' : '#bfccd6',
                background: i === activeIndex ? '#137cbd' : 'transparent',
                whiteSpace: 'nowrap',
                overflow: 'hidden',
                textOverflow: 'ellipsis',
              }}
            >
              {suggestion}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
};

export default AutoCompleteInput;
