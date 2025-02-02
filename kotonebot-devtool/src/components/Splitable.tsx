import React, { useState, useEffect, Children } from 'react';
import styled from '@emotion/styled';
import { useResizePanel } from '../hooks/useResizePanel';

interface SplitableProps {
  children: React.ReactNode;
  /** 是否为垂直分割，默认为水平分割 */
  vertical?: boolean;
  /** 默认是否折叠最后一个面板 */
  defaultCollapsed?: boolean;
  /** 折叠状态改变时的回调 */
  onCollapsedChange?: (collapsed: boolean) => void;
}

const Container = styled.div<{ $vertical?: boolean }>`
  position: relative;
  display: flex;
  flex-direction: ${props => props.$vertical ? 'column' : 'row'};
  width: 100%;
  height: 100%;
  overflow: hidden;
`;

const Panel = styled.div<{ 
  $isLast: boolean, 
  $width: number, 
  $collapsed: boolean,
  $vertical?: boolean,
  $isResizable?: boolean
}>`
  position: relative;
  ${props => props.$isResizable ? `
    ${props.$vertical ? 'height' : 'width'}: ${props.$collapsed ? '0' : `${props.$width}px`};
  ` : `
    flex: 1;
    min-${props.$vertical ? 'height' : 'width'}: 0;
  `}
  ${props => props.$vertical ? 'width: 100%;' : 'height: 100%;'}
  background-color: #fff;
  ${props => !props.$vertical && 'border-left: 1px solid #dee2e6;'}
  ${props => props.$vertical && 'border-top: 1px solid #dee2e6;'}
  overflow: hidden;
`;

const ResizeHandle = styled.div<{ 
  $isResizing: boolean,
  $vertical?: boolean 
}>`
  position: absolute;
  ${props => props.$vertical ? `
    left: 0;
    right: 0;
    top: 0;
    height: 4px;
    cursor: row-resize;
  ` : `
    left: 0;
    top: 0;
    bottom: 0;
    width: 4px;
    cursor: col-resize;
  `}
  background-color: ${props => props.$isResizing ? '#0d6efd' : 'transparent'};
  transition: background-color 0.2s ease;
  z-index: 10;
  
  &:hover {
    background-color: #0d6efd;
  }
`;

const ToggleButton = styled.button<{ 
  $collapsed: boolean,
  $vertical?: boolean 
}>`
  position: absolute;
  ${props => props.$vertical ? `
    bottom: 1rem;
    left: 50%;
    transform: translateX(-50%) rotate(${props.$collapsed ? 90 : -90}deg);
  ` : `
    right: 1rem;
    top: 1rem;
    transform: rotate(${props.$collapsed ? 180 : 0}deg);
  `}
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

  &:hover {
    background-color: #6c757d;
    color: #fff;
  }
`;

export const Splitable: React.FC<SplitableProps> = ({
  children,
  vertical = false,
  defaultCollapsed = false,
  onCollapsedChange
}) => {
  const childrenArray = Children.toArray(children);
  const [collapsed, setCollapsed] = useState(defaultCollapsed);
  const [panelSizes, setPanelSizes] = useState<number[]>(
    Array(childrenArray.length).fill(400)
  );

  // 为每个可调整大小的面板创建一个 useResizePanel 实例
  const resizePanels = childrenArray.map((_, index) => {
    if (index === 0) return null; // 第一个面板不需要调整大小
    return useResizePanel({
      vertical,
      defaultWidth: 400,
      minWidth: 100,
      maxWidth: 800,
      onWidthChange: (width) => {
        setPanelSizes(prev => {
          const newSizes = [...prev];
          newSizes[index] = width;
          return newSizes;
        });
      }
    });
  });

  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      resizePanels.forEach(panel => panel?.handleResizeMove(e));
    };

    const handleMouseUp = () => {
      resizePanels.forEach(panel => panel?.handleResizeEnd());
    };

    const isAnyPanelResizing = resizePanels.some(panel => panel?.isResizing);
    if (isAnyPanelResizing) {
      window.addEventListener('mousemove', handleMouseMove);
      window.addEventListener('mouseup', handleMouseUp);
    }

    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseup', handleMouseUp);
    };
  }, [resizePanels]);

  const handleToggle = () => {
    setCollapsed(prev => {
      const newCollapsed = !prev;
      onCollapsedChange?.(newCollapsed);
      return newCollapsed;
    });
  };

  return (
    <Container $vertical={vertical}>
      {childrenArray.map((child, index) => (
        <Panel
          key={index}
          $isLast={index === childrenArray.length - 1}
          $width={panelSizes[index]}
          $collapsed={index === childrenArray.length - 1 ? collapsed : false}
          $vertical={vertical}
          $isResizable={index !== 0}
        >
          {index > 0 && (
            <ResizeHandle
              onMouseDown={resizePanels[index]?.handleResizeStart}
              $isResizing={resizePanels[index]?.isResizing || false}
              $vertical={vertical}
            />
          )}
          {index === childrenArray.length - 1 && (
            <ToggleButton
              onClick={handleToggle}
              $collapsed={collapsed}
              $vertical={vertical}
            >
              <i className="bi bi-chevron-right" />
            </ToggleButton>
          )}
          {child}
        </Panel>
      ))}
    </Container>
  );
};
