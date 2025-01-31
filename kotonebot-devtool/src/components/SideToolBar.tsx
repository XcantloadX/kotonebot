import React, { useState } from 'react';
import styled from '@emotion/styled';

export interface Tool {
  id: string;
  icon: React.ReactNode;
  title: string;
  onClick?: () => void;
  selectable?: boolean;
}

export interface SideToolBarProps {
  tools: Array<Tool | 'separator'>;
  selectedToolId?: string;
  /**
   * 选择工具事件。
   * 只有 selectable 为 true 的工具才会触发此事件。
   * @param id 工具id
   */
  onSelectTool?: (id: string) => void;
  /**
   * 点击工具事件。
   * 所有工具都会触发此事件。
   * 
   * 可以使用 Tool 对象中的 onClick 事件单独处理每个工具的点击事件，
   * 也可以使用此事件统一处理所有工具的点击事件。
   * 
   * （触发顺序：onClick > onClickTool > onSelectTool）
   * @param id 工具id
   */
  onClickTool?: (id: string) => void;
}

const ToolBarContainer = styled.div`
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 8px;
  border-radius: 8px;
  width: fit-content;

  @media (prefers-color-scheme: dark) {
    background-color: #2c2c2c;
  }

  @media (prefers-color-scheme: light) {
    background-color: #f8f9fa;
    border: 1px solid #dee2e6;
  }
`;

const ToolButton = styled.button<{ isSelected?: boolean }>`
  width: 40px;
  height: 40px;
  padding: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  border: none;
  border-radius: 8px;
  background-color: ${props => props.isSelected ? 'rgba(255, 255, 255, 0.2)' : 'transparent'};
  transition: background-color 0.2s;

  @media (prefers-color-scheme: dark) {
    color: #fff;

    &:hover {
      background-color: ${props => props.isSelected ? 'rgba(255, 255, 255, 0.3)' : 'rgba(255, 255, 255, 0.1)'};
      color: #fff;
    }

    &:active {
      background-color: rgba(255, 255, 255, 0.2);
      color: #fff;
    }

    &:focus {
      color: #fff;
    }
  }

  @media (prefers-color-scheme: light) {
    color: #212529;
    background-color: ${props => props.isSelected ? 'rgba(0, 0, 0, 0.1)' : 'transparent'};

    &:hover {
      background-color: ${props => props.isSelected ? 'rgba(0, 0, 0, 0.15)' : 'rgba(0, 0, 0, 0.05)'};
      color: #212529;
    }

    &:active {
      background-color: rgba(0, 0, 0, 0.1);
      color: #212529;
    }

    &:focus {
      color: #212529;
    }
  }

  // 覆盖 Bootstrap 按钮的默认样式
  &.btn:hover,
  &.btn:active,
  &.btn:focus {
    border: none;
    box-shadow: none;
  }
`;

const Separator = styled.div`
  height: 1px;
  margin: 4px 0;

  @media (prefers-color-scheme: dark) {
    background-color: rgba(255, 255, 255, 0.2);
  }

  @media (prefers-color-scheme: light) {
    background-color: rgba(0, 0, 0, 0.1);
  }
`;

const Tooltip = styled.div<{ visible: boolean }>`
  position: absolute;
  left: 100%;
  top: 50%;
  transform: translateY(-50%);
  margin-left: 8px;
  padding: 4px 8px;
  background-color: rgba(0, 0, 0, 0.75);
  color: white;
  border-radius: 4px;
  font-size: 12px;
  white-space: nowrap;
  pointer-events: none;
  opacity: ${props => props.visible ? 1 : 0};
  transition: opacity 0.2s;
  z-index: 1000;

  &::before {
    content: '';
    position: absolute;
    right: 100%;
    top: 50%;
    transform: translateY(-50%);
    border-width: 4px;
    border-style: solid;
    border-color: transparent rgba(0, 0, 0, 0.75) transparent transparent;
  }
`;

const ToolButtonWrapper = styled.div`
  position: relative;
`;

export const SideToolBar: React.FC<SideToolBarProps> = ({
  tools,
  selectedToolId,
  onSelectTool,
  onClickTool
}) => {
  return (
    <ToolBarContainer>
      {tools.map((tool, index) => {
        if (tool === 'separator') {
          return <Separator key={`separator-${index}`} />;
        }

        const [showTooltip, setShowTooltip] = useState(false);

        const handleClick = () => {
          tool.onClick?.();
          onClickTool?.(tool.id);
          if (tool.selectable !== false && onSelectTool) {
            onSelectTool(tool.id);
          }
        };

        return (
          <ToolButtonWrapper 
            key={`tool-${tool.id}`}
            onMouseEnter={() => setShowTooltip(true)}
            onMouseLeave={() => setShowTooltip(false)}
          >
            <ToolButton
              onClick={handleClick}
              isSelected={tool.selectable !== false && selectedToolId === tool.id}
            >
              {tool.icon}
            </ToolButton>
            <Tooltip visible={showTooltip}>{tool.title}</Tooltip>
          </ToolButtonWrapper>
        );
      })}
    </ToolBarContainer>
  );
};