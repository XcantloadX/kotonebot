import { useCallback, useRef, useState } from 'react';

interface UseResizePanelProps {
  minWidth?: number;
  maxWidth?: number;
  defaultWidth?: number;
  onWidthChange?: (width: number) => void;
}

export const useResizePanel = ({
  minWidth = 200,
  maxWidth = 800,
  defaultWidth = 400,
  onWidthChange
}: UseResizePanelProps = {}) => {
  const [width, setWidth] = useState(defaultWidth);
  const [isResizing, setIsResizing] = useState(false);
  const startXRef = useRef<number>(0);
  const startWidthRef = useRef<number>(0);

  const handleResizeStart = useCallback((event: React.MouseEvent) => {
    event.preventDefault();
    setIsResizing(true);
    startXRef.current = event.clientX;
    startWidthRef.current = width;
    document.body.style.cursor = 'col-resize';
    document.body.style.userSelect = 'none';
  }, [width]);

  const handleResizeMove = useCallback((event: MouseEvent) => {
    if (!isResizing) return;

    const dx = startXRef.current - event.clientX;
    const newWidth = Math.min(Math.max(startWidthRef.current + dx, minWidth), maxWidth);
    
    setWidth(newWidth);
    onWidthChange?.(newWidth);
  }, [isResizing, minWidth, maxWidth, onWidthChange]);

  const handleResizeEnd = useCallback(() => {
    setIsResizing(false);
    document.body.style.cursor = '';
    document.body.style.userSelect = '';
  }, []);

  const togglePanel = useCallback(() => {
    const newWidth = width === 0 ? defaultWidth : 0;
    setWidth(newWidth);
    onWidthChange?.(newWidth);
  }, [width, defaultWidth, onWidthChange]);

  return {
    width,
    isResizing,
    handleResizeStart,
    handleResizeMove,
    handleResizeEnd,
    togglePanel
  };
}; 