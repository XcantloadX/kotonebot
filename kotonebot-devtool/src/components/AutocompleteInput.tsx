import React, { useState, useRef, useEffect } from 'react';
import Form from 'react-bootstrap/Form';
import ListGroup from 'react-bootstrap/ListGroup';
import styled from '@emotion/styled';

const Container = styled.div`
  position: relative;
  width: 100%;
`;

const SuggestionList = styled(ListGroup)`
  position: absolute;
  top: 100%;
  left: 0;
  right: 0;
  z-index: 1000;
  max-height: 200px;
  overflow-y: auto;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
`;

const SuggestionItem = styled(ListGroup.Item)<{ active: boolean }>`
  cursor: pointer;
  background-color: ${props => props.active ? '#0d6efd' : 'white'};
  color: ${props => props.active ? 'white' : 'inherit'};
  &:hover {
    background-color: ${props => props.active ? '#0d6efd' : '#e9ecef'};
    color: ${props => props.active ? 'white' : 'inherit'};
  }
`;

interface AutocompleteInputProps extends Omit<React.ComponentProps<typeof Form.Control>, 'onChange'> {
  onAutoCompleteRequest: (value: string) => string[] | Promise<string[]>;
  onChange?: (value: string) => void;
  onAutocompleteSelect?: (inputValue: string, selectOption: string) => string | Promise<string>;
  debounceTime?: number;
}

export default function AutocompleteInput({
  onAutoCompleteRequest: onAutoComplete,
  onChange,
  onAutocompleteSelect,
  debounceTime = 100,
  ...props
}: AutocompleteInputProps) {
  const [value, setValue] = useState('');
  const [previousValue, setPreviousValue] = useState('');
  const [suggestions, setSuggestions] = useState<string[]>([]);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [selectedIndex, setSelectedIndex] = useState(-1);
  const [loading, setLoading] = useState(false);
  const [showLoading, setShowLoading] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);
  const timeoutRef = useRef<NodeJS.Timeout>();
  const loadingTimeoutRef = useRef<NodeJS.Timeout>();
  const selectedItemRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    // 组件卸载时清除所有定时器
    return () => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }
      if (loadingTimeoutRef.current) {
        clearTimeout(loadingTimeoutRef.current);
      }
    };
  }, []);

  // 添加选中项变化时的滚动效果
  useEffect(() => {
    if (selectedIndex >= 0 && selectedItemRef.current) {
      selectedItemRef.current.scrollIntoView({
        block: 'nearest',
        behavior: 'smooth'
      });
    }
  }, [selectedIndex]);

  const handleInputChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const newValue = e.target.value;
    setPreviousValue(value);
    setValue(newValue);
    onChange?.(newValue);

    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
    }
    if (loadingTimeoutRef.current) {
      clearTimeout(loadingTimeoutRef.current);
    }

    if (newValue.trim()) {
      setLoading(true);
      // 设置加载提示的延迟显示
      loadingTimeoutRef.current = setTimeout(() => {
        if (loading) {
          setShowLoading(true);
        }
      }, 300);

      timeoutRef.current = setTimeout(async () => {
        try {
          const result = await onAutoComplete(newValue);
          setSuggestions(result);
          setShowSuggestions(true);
          setSelectedIndex(result.length > 0 ? 0 : -1);
        } catch (error) {
          console.error('自动完成请求失败:', error);
          setSuggestions([]);
        } finally {
          setLoading(false);
          setShowLoading(false);
          if (loadingTimeoutRef.current) {
            clearTimeout(loadingTimeoutRef.current);
          }
        }
      }, debounceTime);
    } else {
      setSuggestions([]);
      setShowSuggestions(false);
    }
  };

  const handleSelectSuggestion = async (suggestion: string) => {
    setPreviousValue(value);
    let finalValue = suggestion;
    if (onAutocompleteSelect) {
      try {
        finalValue = await onAutocompleteSelect(value, suggestion);
      } catch (error) {
        console.error('处理选择值时发生错误:', error);
      }
    }
    setValue(finalValue);
    onChange?.(finalValue);
    setShowSuggestions(false);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if ((e.ctrlKey || e.metaKey) && e.key === 'z') {
      e.preventDefault();
      setValue(previousValue);
      onChange?.(previousValue);
      return;
    }

    if (!showSuggestions) return;

    switch (e.key) {
      case 'ArrowDown':
        e.preventDefault();
        setSelectedIndex(prev => 
          prev < suggestions.length - 1 ? prev + 1 : prev
        );
        break;
      case 'ArrowUp':
        e.preventDefault();
        setSelectedIndex(prev => prev > -1 ? prev - 1 : prev);
        break;
      case 'Tab':
      case 'Enter':
        e.preventDefault();
        if (selectedIndex >= 0) {
          handleSelectSuggestion(suggestions[selectedIndex]);
        }
        break;
      case 'Escape':
        setShowSuggestions(false);
        break;
    }
  };

  const handleSuggestionClick = (suggestion: string) => {
    handleSelectSuggestion(suggestion);
  };

  // 点击外部时关闭建议列表
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setShowSuggestions(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, []);

  return (
    <Container ref={containerRef}>
      <Form.Control
        {...props}
        value={value}
        onChange={handleInputChange}
        onKeyDown={handleKeyDown}
        autoComplete="off"
      />
      {showSuggestions && suggestions.length > 0 && (
        <SuggestionList>
          {showLoading ? (
            <ListGroup.Item>加载中...</ListGroup.Item>
          ) : (
            suggestions.map((suggestion, index) => (
              <SuggestionItem
                key={suggestion}
                active={index === selectedIndex}
                onClick={() => handleSuggestionClick(suggestion)}
                ref={index === selectedIndex ? selectedItemRef : undefined}
              >
                {suggestion}
              </SuggestionItem>
            ))
          )}
        </SuggestionList>
      )}
    </Container>
  );
}
