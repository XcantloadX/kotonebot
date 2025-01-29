import React, { useState, useEffect } from 'react';
import styled from '@emotion/styled';
import { useResizePanel } from '../hooks/useResizePanel';

interface SplitableProps {
  left: React.ReactNode;
  right: React.ReactNode;
  /** 默认是否折叠右侧面板 */
  defaultCollapsed?: boolean;
  /** 折叠状态改变时的回调 */
  onCollapsedChange?: (collapsed: boolean) => void;
}

const Container = styled.div`
  position: relative;
  display: flex;
  width: 100%;
  height: 100%;
  overflow: hidden;
`;

const LeftPanel = styled.div`
  flex: 1;
  min-width: 0;
`;

const RightPanel = styled.div<{ $width: number; $collapsed: boolean }>`
  position: relative;
  width: ${props => props.$collapsed ? '0' : `${props.$width}px`};
  height: 100%;
  background-color: #fff;
  border-left: 1px solid #dee2e6;
  overflow: hidden;
`;

const ResizeHandle = styled.div<{ $isResizing: boolean }>`
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 4px;
  background-color: ${props => props.$isResizing ? '#0d6efd' : 'transparent'};
  transition: background-color 0.2s ease;
  cursor: col-resize;
  z-index: 1;
  
  &:hover {
    background-color: #0d6efd;
  }
`;

const ToggleButton = styled.button<{ $collapsed: boolean }>`
  position: absolute;
  right: 1rem;
  top: 1rem;
  z-index: 2;
  padding: 0.25rem 0.5rem;
  font-size: 0.875rem;
  line-height: 1.5;
  border-radius: 0.2rem;
  border: 1px solid #6c757d;
  background-color: transparent;
  color: #6c757d;
  cursor: pointer;
  transition: transform 0.3s ease;
  transform: rotate(${props => props.$collapsed ? 180 : 0}deg);

  &:hover {
    background-color: #6c757d;
    color: #fff;
  }
`;

export const Splitable: React.FC<SplitableProps> = ({
  left,
  right,
  defaultCollapsed = false,
  onCollapsedChange
}) => {
  const {
    width,
    isResizing,
    handleResizeStart,
    handleResizeMove,
    handleResizeEnd,
  } = useResizePanel();

  const [collapsed, setCollapsed] = useState(defaultCollapsed);

  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      handleResizeMove(e);
    };

    const handleMouseUp = () => {
      handleResizeEnd();
    };

    if (isResizing) {
      window.addEventListener('mousemove', handleMouseMove);
      window.addEventListener('mouseup', handleMouseUp);
    }

    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseup', handleMouseUp);
    };
  }, [isResizing, handleResizeMove, handleResizeEnd]);

  const handleToggle = () => {
    setCollapsed(prev => {
      const newCollapsed = !prev;
      onCollapsedChange?.(newCollapsed);
      return newCollapsed;
    });
  };

  return (
    <Container>
      <ToggleButton
        onClick={handleToggle}
        $collapsed={collapsed}
      >
        <i className="bi bi-chevron-right" />
      </ToggleButton>
      <LeftPanel>
        {left}
      </LeftPanel>
      <RightPanel $width={width} $collapsed={collapsed}>
        <ResizeHandle
          onMouseDown={handleResizeStart}
          $isResizing={isResizing}
        />
        {right}
      </RightPanel>
    </Container>
  );
};
