import styled from '@emotion/styled';
import { RectPoints } from './types';
import { useEffect, useRef, ReactNode } from 'react';
import NativeDiv from '../NativeDiv';
type RectMode = 'move' | 'resize' | 'none';

const Handle = styled(NativeDiv)<{ $mode: RectMode }>`
  position: absolute;
  width: 12px;
  height: 12px;
  background: white;
  border: 1px solid #666;
  transform: translate(-50%, -50%);
  cursor: pointer;
  z-index: 2;
  box-sizing: border-box;
  display: ${props => props.$mode === 'resize' ? 'block' : 'none'};
`;

const ResizeArea = styled(NativeDiv)<{ position: string }>`
  position: absolute;
  z-index: 1;
  width: 100%;
  ${props => {
    switch (props.position) {
      case 'top':
        return 'top: -3px; left: 0; height: 6px; cursor: n-resize;';
      case 'bottom':
        return 'bottom: -3px; left: 0; height: 6px; cursor: s-resize;';
      case 'left':
        return 'left: -3px; top: 0; bottom: 0; width: 6px; cursor: w-resize;';
      case 'right':
        return 'right: -3px; top: 0; bottom: 0; width: 6px; cursor: e-resize;';
      default:
        return '';
    }
  }}
`;

const RectBoxContainer = styled(NativeDiv)<{ rect: RectPoints; mode: RectMode; $lineColor: string }>`
  position: absolute;
  border: 3px solid ${props => props.$lineColor};
  transition: border 0.1s ease-in;
  background: transparent;
  left: ${props => props.rect.x1}px;
  top: ${props => props.rect.y1}px;
  width: ${props => Math.abs(props.rect.x2 - props.rect.x1)}px;
  height: ${props => Math.abs(props.rect.y2 - props.rect.y1)}px;
`;

const DragArea = styled(NativeDiv)`
  position: absolute;
  z-index: 1;
  width: 100%;
  height: 100%;
  cursor: move;
`;

const RectTipContainer = styled(NativeDiv)`
  position: absolute;
  top: calc(-3px);
  left: 0;
  z-index: 3;
  transform: translateY(-100%);
`;

export interface RectBoxProps {
  rect: RectPoints;
  /**
   * 矩形模式。默认为 resize。
   * 
   * * move: 移动。不显示四个角上的把手，只允许整体移动矩形。
   * * resize: 调整大小。显示四个角上的把手，同时允许调整矩形的大小和移动。
   * * none: 无。不显示四个把手，也不允许移动和调整大小。
   */
  mode?: RectMode;
  /**
   * 矩形框的线条颜色。默认为白色。
   */
  lineColor?: string;
  /**
   * 显示在矩形框上方的提示内容
   */
  rectTip?: ReactNode;
  /**
   * 是否显示提示内容（`rectTip`）
   */
  showRectTip?: boolean;
  /**
   * 矩形框变换事件。
   * 
   * 变换后的坐标是在原坐标的基础上加上拖拽时鼠标的位移差得到的。
   * 也就是说，原来传入的是什么坐标系的坐标，变换后的坐标也是什么坐标系的坐标。
   * @param points 变换后的矩形框
   */
  onTransform?: (points: RectPoints) => void;
  onNativeMouseEnter?: (e: MouseEvent) => void;
  onNativeMouseMove?: (e: MouseEvent) => void;
  onNativeMouseLeave?: (e: MouseEvent) => void;
  onNativeClick?: (e: MouseEvent) => void;
}

type DragSource = 
  'top-edge' | 'bottom-edge' | 'left-edge' | 'right-edge' | 
  'top-left-corner' | 'top-right-corner' | 'bottom-left-corner' | 'bottom-right-corner' |
  'move' |
  null;

function useLatestProps<T>(props: T) {
  const ref = useRef(props);
  useEffect(() => {
    ref.current = props;
  }, [props]);
  return ref;
}

/**
 * 可调整位置、大小的矩形框组件。
 */
function RectBox(props: RectBoxProps) {
  const { 
    rect, 
    mode = 'resize', 
    lineColor = 'white', 
    rectTip,
    showRectTip = false,
    onTransform, 
    onNativeMouseEnter, 
    onNativeMouseLeave, 
    onNativeClick 
  } = props;
  const dragRef = useRef({
    dragging: false,
    source: null as DragSource,
    mouseStartX: 0,
    mouseStartY: 0,
    originalRect: null as RectPoints | null,
    newRect: null as RectPoints | null,
  });
  const propsRef = useLatestProps(props);
  const containerRef = useRef<HTMLDivElement>(null);

  const handleMouseDown = (e: MouseEvent, source: DragSource) => {
    e.preventDefault();
    e.stopPropagation();
    const { rect } = propsRef.current;
    dragRef.current.dragging = true;
    dragRef.current.source = source;
    dragRef.current.mouseStartX = e.clientX;
    dragRef.current.mouseStartY = e.clientY;
    dragRef.current.originalRect = rect;
    dragRef.current.newRect = rect;
    console.log('RectBox: handleMouseDown', source, dragRef.current.newRect);
  };

  const handleMouseMove = (e: MouseEvent) => {
    if (!dragRef.current.dragging || !dragRef.current.originalRect) return;
    e.preventDefault();
    e.stopPropagation();
    const deltaX = e.clientX - dragRef.current.mouseStartX;
    const deltaY = e.clientY - dragRef.current.mouseStartY;
    
    const startX = dragRef.current.originalRect.x1;
    const startY = dragRef.current.originalRect.y1;
    const endX = dragRef.current.originalRect.x2;
    const endY = dragRef.current.originalRect.y2;
    const points = {x1: startX, y1: startY, x2: endX, y2: endY};
    
    if (dragRef.current.source === 'top-edge')
      points.y1 = startY + deltaY;
    else if (dragRef.current.source === 'bottom-edge')
      points.y2 = endY + deltaY;
    else if (dragRef.current.source === 'left-edge')
      points.x1 = startX + deltaX;
    else if (dragRef.current.source === 'right-edge')
      points.x2 = endX + deltaX;
    else if (dragRef.current.source === 'top-left-corner') {
      points.x1 = startX + deltaX;
      points.y1 = startY + deltaY;
    }
    else if (dragRef.current.source === 'top-right-corner') {
      points.x2 = endX + deltaX;
      points.y1 = startY + deltaY;
    }
    else if (dragRef.current.source === 'bottom-left-corner') {
      points.x1 = startX + deltaX;
      points.y2 = endY + deltaY;
    }
    else if (dragRef.current.source === 'bottom-right-corner') {
      points.x2 = endX + deltaX;
      points.y2 = endY + deltaY;
    }
    else if (dragRef.current.source === 'move') {
      points.x1 = startX + deltaX;
      points.y1 = startY + deltaY;
      points.x2 = endX + deltaX;
      points.y2 = endY + deltaY;
    }
    
    console.log('RectBox: handleMouseMove', dragRef.current.source);
    dragRef.current.newRect = points;
    onTransform?.(points);
  };

  const handleMouseUp = (e: MouseEvent) => {
    if (!dragRef.current.dragging || !dragRef.current.newRect) return;
    e.preventDefault();
    e.stopPropagation();
    console.log('RectBox: handleMouseUp');
    onTransform?.({ ...dragRef.current.newRect });
    dragRef.current.dragging = false;
    dragRef.current.source = null;
    dragRef.current.mouseStartX = 0;
    dragRef.current.mouseStartY = 0;
    dragRef.current.originalRect = null;
    dragRef.current.newRect = null;
  };

  const handleClick = (e: MouseEvent) => {
    console.log('RectBox: handleClick');
    e.stopPropagation();
    if (!dragRef.current.dragging) {
      onNativeClick?.(e);
    }
  };

  const stopPropagation = (e: MouseEvent) => {
    console.log('RectBox: stopPropagation', e);
    e.stopPropagation();
  };
  const makeEvents = (source: DragSource) => ({
    onNativeMouseDown: (e: MouseEvent) => handleMouseDown(e, source),

  });

  useEffect(() => {
    document.addEventListener('mousemove', handleMouseMove);
    document.addEventListener('mouseup', handleMouseUp);
    return () => {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
    };
  }, []);

  return (
    <RectBoxContainer 
      ref={containerRef}
      rect={rect}
      mode={mode}
      $lineColor={lineColor}
    >
      {showRectTip && rectTip && (
        <RectTipContainer>
          {rectTip}
        </RectTipContainer>
      )}
      <DragArea
        {...makeEvents('move')}
        onNativeMouseEnter={onNativeMouseEnter}
        onNativeMouseLeave={onNativeMouseLeave}
        onNativeClick={handleClick}
      />
      {mode === 'resize' && (
        <>
          <ResizeArea position="top" {...makeEvents('top-edge')} onNativeClick={stopPropagation} />
          <ResizeArea position="bottom" {...makeEvents('bottom-edge')} onNativeClick={stopPropagation} />
          <ResizeArea position="left" {...makeEvents('left-edge')} onNativeClick={stopPropagation} />
          <ResizeArea position="right" {...makeEvents('right-edge')} onNativeClick={stopPropagation} />
          
          <Handle $mode={mode} style={{ left: 0, top: 0, cursor: 'nw-resize' }}
            {...makeEvents('top-left-corner')}
            onNativeClick={stopPropagation}
          />
          <Handle $mode={mode} style={{ left: '100%', top: 0, cursor: 'ne-resize' }}
            {...makeEvents('top-right-corner')}
            onNativeClick={stopPropagation}
          />
          <Handle $mode={mode} style={{ left: 0, top: '100%', cursor: 'sw-resize' }}
            {...makeEvents('bottom-left-corner')}
            onNativeClick={stopPropagation}
          />
          <Handle $mode={mode} style={{ left: '100%', top: '100%', cursor: 'se-resize' }}
            {...makeEvents('bottom-right-corner')}
            onNativeClick={stopPropagation}
          />
        </>
      )}
    </RectBoxContainer>
  );
};

export default RectBox;
