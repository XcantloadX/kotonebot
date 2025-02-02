import React, { useState, useRef, useEffect } from 'react';
import styled from '@emotion/styled';

const DropdownContainer = styled.div`
  position: relative;
  display: inline-block;
`;

const DropdownButton = styled.button<{ $isOpen: boolean }>`
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 4px 8px;
  background-color: white;
  border: 1px solid #e7e7e7;
  border-radius: 2px;
  cursor: pointer;
  font-size: 13px;
  color: #424242;
  min-width: 100px;
  justify-content: space-between;

  &:hover {
    background-color: #e0e0e0;
  }

  &:active {
    background-color: #d0d0d0;
  }
`;

const DropdownArrow = styled.span<{ $isOpen: boolean }>`
  border-style: solid;
  border-width: 4px 4px 0 4px;
  border-color: #424242 transparent transparent transparent;
  margin-left: 4px;
  transform: ${props => props.$isOpen ? 'rotate(180deg)' : 'rotate(0)'};
  transition: transform 0.2s ease;
`;

const DropdownMenu = styled.div<{ $isOpen: boolean }>`
  position: absolute;
  top: 100%;
  left: 0;
  width: 100%;
  background-color: #ffffff;
  border: 1px solid #e7e7e7;
  border-radius: 2px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  z-index: 1000;
  display: ${props => props.$isOpen ? 'block' : 'none'};
  margin-top: 2px;
`;

const MenuItem = styled.div<{ $selected?: boolean }>`
  padding: 6px 8px;
  cursor: pointer;
  font-size: 13px;
  color: #424242;
  background-color: ${props => props.$selected ? '#e8e8e8' : 'transparent'};

  &:hover {
    background-color: #f0f0f0;
  }
`;

export interface DropdownOption {
  value: string;
  label: string;
}

interface VSDropdownProps {
  options: DropdownOption[];
  value?: string;
  onChange?: (value: string) => void;
  placeholder?: string;
  className?: string;
  style?: React.CSSProperties;
}

export const VSDropdown: React.FC<VSDropdownProps> = ({
  options,
  value,
  onChange,
  placeholder = '请选择...',
  className,
  style
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  const selectedOption = options.find(opt => opt.value === value);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, []);

  const handleSelect = (option: DropdownOption) => {
    onChange?.(option.value);
    setIsOpen(false);
  };

  return (
    <DropdownContainer ref={containerRef} className={className} style={style}>
      <DropdownButton 
        onClick={() => setIsOpen(!isOpen)}
        $isOpen={isOpen}
      >
        <span>{selectedOption?.label || placeholder}</span>
        <DropdownArrow $isOpen={isOpen} />
      </DropdownButton>
      <DropdownMenu $isOpen={isOpen}>
        {options.map((option) => (
          <MenuItem
            key={option.value}
            onClick={() => handleSelect(option)}
            $selected={option.value === value}
          >
            {option.label}
          </MenuItem>
        ))}
      </DropdownMenu>
    </DropdownContainer>
  );
};

// 导出命名空间对象
const Dropdown = Object.assign(VSDropdown, {});

export default Dropdown; 