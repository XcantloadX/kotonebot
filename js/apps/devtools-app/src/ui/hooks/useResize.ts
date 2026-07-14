import { useCallback, useRef } from 'react';

export type ResizeDirection = 'horizontal' | 'vertical';

export interface UseResizeOptions {
  direction: ResizeDirection;
  minSize: number;
  maxSize?: number | (() => number);
  size: number;
  onSizeChange: (size: number) => void;
  enabled?: boolean;
}

export interface ResizeHandleProps {
  onMouseDown: (e: React.MouseEvent<HTMLDivElement>) => void;
  style: React.CSSProperties;
}

export function useResize(options: UseResizeOptions) {
  const { direction, minSize, maxSize, size, onSizeChange, enabled = true } = options;
  const optionsRef = useRef(options);
  optionsRef.current = options;

  const handleMouseDown = useCallback(
    (e: React.MouseEvent<HTMLDivElement>) => {
      if (!enabled) return;
      e.preventDefault();

      const { direction, minSize, maxSize, size, onSizeChange } = optionsRef.current;
      const startPos = direction === 'horizontal' ? e.clientX : e.clientY;
      const startSize = size;

      const resolveMaxSize = () => {
        if (typeof maxSize === 'function') return maxSize();
        if (maxSize !== undefined) return maxSize;
        return direction === 'horizontal' ? window.innerWidth * 0.6 : window.innerHeight * 0.6;
      };

      const onMove = (ev: MouseEvent) => {
        const currentPos = direction === 'horizontal' ? ev.clientX : ev.clientY;
        const delta = direction === 'horizontal' ? startPos - currentPos : startPos - currentPos;
        const next = Math.max(minSize, Math.min(resolveMaxSize(), startSize + delta));
        onSizeChange(next);
      };

      const onUp = () => {
        window.removeEventListener('mousemove', onMove);
        window.removeEventListener('mouseup', onUp);
      };

      window.addEventListener('mousemove', onMove);
      window.addEventListener('mouseup', onUp);
    },
    [enabled]
  );

  const handleProps: ResizeHandleProps = {
    onMouseDown: handleMouseDown,
    style: {
      cursor: direction === 'horizontal' ? 'col-resize' : 'row-resize',
      ...(direction === 'horizontal'
        ? { width: 4, height: '100%' }
        : { height: 4, width: '100%' }),
    },
  };

  return { handleMouseDown, handleProps };
}
