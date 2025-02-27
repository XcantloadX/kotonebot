import { EditorTool, ToolProps } from '../core/types';
import { useEffect } from 'react';
import useLatestCallback from '../../../hooks/useLatestCallback';
import { Annotation } from '../types';
import { v4 } from 'uuid';

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
    </>
  );
}

const PointTool: EditorTool = {
  name: 'point',
  cursor: 'crosshair',
  Component: PointToolComponent
};

export default PointTool;
