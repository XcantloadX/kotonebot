import React, { useState, useRef, useEffect } from 'react';
import styled from '@emotion/styled';

// 基础工具接口
interface BaseToolProps {
  id: string;
  title?: string;
  disabled?: boolean;
  selected?: boolean;
}

// 按钮类型工具
export interface ButtonTool extends BaseToolProps {
  type: 'button';
  icon: React.ReactNode;
  label?: string;
  onClick: () => void;
}

// Checkbox类型工具
export interface CheckboxTool extends BaseToolProps {
  type: 'checkbox';
  label: React.ReactNode;
  checked: boolean;
  onChange: (e: React.ChangeEvent<HTMLInputElement>) => void;
}

// 分隔符类型
export type SeparatorTool = 'separator';

// 添加 Dropdown 相关组件
const DropdownContainer = styled.div`
  position: relative;
  display: inline-block;
`;

const DropdownButton = styled.button<{ $isOpen: boolean }>`
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 4px 8px;
  background-color: #f3f3f3;
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

interface ToolDropdownProps extends BaseToolProps {
  type: 'dropdown';
  options: DropdownOption[];
  value?: string;
  onChange?: (value: string) => void;
  placeholder?: string;
}

// 合并所有工具类型
export type Tool = ButtonTool | CheckboxTool | ToolDropdownProps;
export type ToolBarItem = Tool | SeparatorTool | React.ReactNode;

interface VSToolBarProps {
  children?: React.ReactNode;
  className?: string;
  align?: 'left' | 'center' | 'right';
  style?: React.CSSProperties;
}

// 样式组件定义
const ToolBarContainer = styled.div<{ $align?: 'left' | 'center' | 'right' }>`
  display: flex;
  flex-direction: row;
  background-color: #f3f3f3;
  border-bottom: 1px solid #e7e7e7;
  padding: 4px;
  gap: 2px;
  align-items: center;
  justify-content: ${props => {
    switch (props.$align) {
      case 'center':
        return 'center';
      case 'right':
        return 'flex-end';
      default:
        return 'flex-start';
    }
  }};
`;

const StyledToolButton = styled.button<{ hasLabel?: boolean; $selected?: boolean; $disabled?: boolean }>`
  display: flex;
  align-items: center;
  justify-content: center;
  height: 32px;
  border: none;
  background-color: ${props => props.$selected ? '#d0d0d0' : 'transparent'};
  cursor: ${props => props.$disabled ? 'not-allowed' : 'pointer'};
  position: relative;
  padding: ${props => props.hasLabel ? '0 8px' : '0'};
  min-width: ${props => props.hasLabel ? '0' : '32px'};
  color: ${props => props.$disabled ? '#a0a0a0' : '#424242'};
  font-size: 16px;
  gap: 4px;
  opacity: ${props => props.$disabled ? 0.6 : 1};

  &:hover {
    background-color: ${props => props.$disabled ? 'transparent' : props.$selected ? '#c0c0c0' : '#e0e0e0'};
  }

  &:active {
    background-color: ${props => props.$disabled ? 'transparent' : props.$selected ? '#b0b0b0' : '#d0d0d0'};
  }

  &[data-tooltip]:hover::after {
    content: attr(data-tooltip);
    position: absolute;
    bottom: -24px;
    left: 50%;
    transform: translateX(-50%);
    background-color: #333;
    color: white;
    padding: 4px 8px;
    border-radius: 4px;
    font-size: 12px;
    white-space: nowrap;
    z-index: 1000;
  }
`;

const ButtonLabel = styled.span`
  font-size: 13px;
`;

const CheckboxContainer = styled.label`
  display: flex;
  align-items: center;
  height: 32px;
  padding: 0 8px;
  cursor: pointer;
  color: #424242;
  gap: 6px;
  user-select: none;

  &:hover {
    background-color: #e0e0e0;
  }
`;

const StyledCheckbox = styled.input`
  appearance: none;
  width: 16px;
  height: 16px;
  border: 1px solid #a0a0a0;
  border-radius: 2px;
  margin: 0;
  cursor: pointer;
  position: relative;
  background: white;

  &:checked {
    background: white;
    &::after {
      content: '';
      position: absolute;
      left: 4px;
      top: 1px;
      width: 6px;
      height: 10px;
      border: solid #000;
      border-width: 0 2px 2px 0;
      transform: rotate(45deg);
    }
  }

  &:hover {
    border-color: #808080;
  }
`;

const Separator = styled.div`
  width: 1px;
  height: 24px;
  margin: 4px 4px;
  background-color: #e0e0e0;
`;

// 组件接口定义
interface ToolButtonProps {
  id: string;
  icon?: React.ReactNode;
  label?: React.ReactNode;
  title?: string;
  onClick?: () => void;
  selected?: boolean;
  disabled?: boolean;
}

interface ToolCheckboxProps {
  id: string;
  label: React.ReactNode;
  checked: boolean;
  title?: string;
  onChange: (e: React.ChangeEvent<HTMLInputElement>) => void;
}

// 子组件定义
export const ToolButton: React.FC<ToolButtonProps> = ({
  id,
  icon,
  label,
  title,
  onClick,
  selected,
  disabled
}) => {
  return (
    <StyledToolButton
      hasLabel={!!label}
      onClick={disabled ? undefined : onClick}
      data-tooltip={label ? undefined : title}
      $selected={selected}
      $disabled={disabled}
      disabled={disabled}
    >
      {icon}
      {label && <ButtonLabel>{label}</ButtonLabel>}
    </StyledToolButton>
  );
};

export const ToolCheckbox: React.FC<ToolCheckboxProps> = ({
  id,
  label,
  checked,
  onChange
}) => {
  return (
    <CheckboxContainer>
      <StyledCheckbox
        type="checkbox"
        id={id}
        checked={checked}
        onChange={onChange}
      />
      <ButtonLabel>{label}</ButtonLabel>
    </CheckboxContainer>
  );
};

export const ToolSeparator: React.FC = () => <Separator />;

// 添加 ToolDropdown 组件
export const ToolDropdown: React.FC<ToolDropdownProps> = ({
  options,
  value,
  onChange,
  placeholder = '请选择...',
  title
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
    <DropdownContainer ref={containerRef} data-tooltip={title}>
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

// 主组件
export const VSToolBar: React.FC<VSToolBarProps> = ({
  children,
  className,
  align = 'left',
  style
}) => {
  return (
    <ToolBarContainer className={className} $align={align} style={style}>
      {children}
    </ToolBarContainer>
  );
};

// 导出命名空间对象
const ToolBar = Object.assign(VSToolBar, {
  Button: ToolButton,
  Checkbox: ToolCheckbox,
  Separator: ToolSeparator,
  Dropdown: ToolDropdown
});

export default ToolBar;
