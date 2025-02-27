import { EditorTool, ToolProps } from '../core/types';
import { useState, useRef, useEffect } from 'react';
import RectBox from '../RectBox';
import useLatestCallback from '../../../hooks/useLatestCallback';
import { Point, Annotation } from '../types';
import { v4 } from 'uuid';

function RectToolComponent(props: ToolProps) {
  const { containerRef, Convertor, addAnnotation, editorProps } = props;
  const [rectStart, setRectStart] = useState<Point | null>(null);
  const [rectEnd, setRectEnd] = useState<Point | null>(null);
  const drawingRef = useRef(false);

  // 处理拖拽开始
  const handleMouseDown = useLatestCallback((e: MouseEvent) => {
    e.preventDefault();
    const rect = containerRef.current?.getBoundingClientRect();
    if (rect) {
      const x = e.clientX - rect.left;
      const y = e.clientY - rect.top;
      setRectStart({ x, y });
      setRectEnd({ x, y });
    }
    drawingRef.current = true;
  });

  // 处理拖拽过程
  const handleMouseMove = useLatestCallback((e: MouseEvent) => {
    const rect = containerRef.current?.getBoundingClientRect();
    if (!rect) return;

    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    setRectEnd({ x, y });
  });

  // 处理拖拽结束
  const handleMouseUp = useLatestCallback(() => {
    if (!rectStart || !rectEnd) return;
    let x1 = Math.min(rectStart.x, rectEnd.x);
    let y1 = Math.min(rectStart.y, rectEnd.y);
    let x2 = Math.max(rectStart.x, rectEnd.x);
    let y2 = Math.max(rectStart.y, rectEnd.y);
    
    if (Math.abs(x1 - x2) < 10 || Math.abs(y1 - y2) < 10) {
      console.log('RectTool: rect too small. skip add annotation');
    }
    else {
      let newRect = { x1, y1, x2, y2 };
      newRect = Convertor.rectContainer2Image(newRect);
      
      const annotation: Annotation = {
        id: v4(),
        type: 'rect',
        data: newRect
      };
      addAnnotation(annotation);
      editorProps.onAnnotationSelected?.(annotation);
    }
    setRectStart(null);
    setRectEnd(null);
    drawingRef.current = false;
  });

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    container.addEventListener('mousedown', handleMouseDown);
    container.addEventListener('mousemove', handleMouseMove);
    container.addEventListener('mouseup', handleMouseUp);

    return () => {
      container.removeEventListener('mousedown', handleMouseDown);
      container.removeEventListener('mousemove', handleMouseMove);
      container.removeEventListener('mouseup', handleMouseUp);
    };
  }, [containerRef.current]);

  return (
    <>
      {rectStart && rectEnd && (
        <RectBox 
          rect={{x1: rectStart.x, y1: rectStart.y, x2: rectEnd.x, y2: rectEnd.y}} 
        />
      )}
    </>
  );
}

const RectTool: EditorTool = {
  name: 'rect',
  cursor: 'crosshair',
  Component: RectToolComponent
};

export default RectTool; 