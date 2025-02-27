import { EditorTool, ToolProps } from '../core/types';
import { useEffect } from 'react';
import useLatestCallback from '../../../hooks/useLatestCallback';
import { Annotation } from '../types';
import { v4 } from 'uuid';
import styled from '@emotion/styled';

const PointMarker = styled.div<{x: number; y: number; isNew?: boolean}>`
  position: absolute;
  width: 20px;
  height: 20px;
  transform: translate(${props => props.x - 10}px, ${props => props.y - 10}px);
  pointer-events: none;

  &::before {
    content: '';
    position: absolute;
    width: 100%;
    height: 100%;
    border-radius: 50%;
    background: rgba(0, 119, 255, 0.5);
    border: 2px solid #1298fe;
  }

  &::after {
    content: '';
    position: absolute;
    top: 50%;
    left: 50%;
    width: 6px;
    height: 6px;
    background: #1298fe;
    border-radius: 50%;
    transform: translate(-50%, -50%);
  }
`;

function PointToolComponent(props: ToolProps) {
  const { containerRef, Convertor, addAnnotation, editorProps } = props;

  const handleClick = useLatestCallback((e: MouseEvent) => {
    e.preventDefault();
    const rect = containerRef.current?.getBoundingClientRect();
    if (!rect) return;

    // 获取点击位置
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    
    // 转换为图片坐标
    const imagePos = Convertor.posContainer2Image({ x, y });
    
    // 创建新的标注
    const annotation: Annotation = {
      id: v4(),
      type: 'point',
      data: imagePos
    };

    // 添加标注并触发选中事件
    addAnnotation(annotation);
    editorProps.onAnnotationSelected?.(annotation);
  });

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    container.addEventListener('click', handleClick);

    return () => {
      container.removeEventListener('click', handleClick);
    };
  }, [containerRef.current]);

  return (
    <>
      {editorProps.annotations.map(anno => {
        if (anno.type !== 'point') return null;
        const data = anno.data as Point;
        const pos = Convertor.posImage2Container(data);
        return (
          <PointMarker
            key={anno.id}
            x={pos.x}
            y={pos.y}
          />
        );
      })}
    </>
  );
}

const PointTool: EditorTool = {
  name: 'point',
  cursor: 'crosshair',
  Component: PointToolComponent
};

export default PointTool;
