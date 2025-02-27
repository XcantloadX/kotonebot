import { EditorTool, ToolProps } from '../core/types';
import { useEffect, useState } from 'react';
import RectBox from '../RectBox';
import RectMask from '../RectMask';
import useLatestCallback from '../../../hooks/useLatestCallback';
import { Annotation, RectPoints } from '../types';

function DragToolComponent(props: ToolProps) {
  const [state, setState] = props.editorState;
  const { containerRef, Convertor, updateAnnotation, queryAnnotation, editorProps } = props;
  const [hoveredRectId, setHoveredRectId] = useState<string | null>(null);
  const [selectedRectId, setSelectedRectId] = useState<string | null>(null);

  // 处理拖拽开始
  const handleMouseDown = useLatestCallback((e: React.MouseEvent) => {
    e.preventDefault();
    if (selectedRectId !== null || hoveredRectId !== null) return;
    
    setState(prev => ({
      ...prev,
      isDragging: true,
      dragStart: {
        x: e.clientX - prev.imagePosition.x,
        y: e.clientY - prev.imagePosition.y,
      }
    }));
  });

  // 处理拖拽过程
  const handleMouseMove = useLatestCallback((e: MouseEvent) => {
    if (!state.isDragging) return;
    const rect = containerRef.current?.getBoundingClientRect();
    if (!rect) return;

    setState(prev => ({
      ...prev,
      imagePosition: {
        x: e.clientX - prev.dragStart.x,
        y: e.clientY - prev.dragStart.y,
      },
      mousePosition: {
        x: e.clientX - rect.left,
        y: e.clientY - rect.top
      }
    }));
  });

  // 处理拖拽结束
  const handleMouseUp = useLatestCallback(() => {
    setState(prev => ({
      ...prev,
      isDragging: false
    }));
  });

  // 处理矩形变换
  const handleRectTransform = useLatestCallback((rectPoints: RectPoints, id: string) => {
    const rect = Convertor.rectContainer2Image({
      x1: rectPoints.x1,
      y1: rectPoints.y1,
      x2: rectPoints.x2,
      y2: rectPoints.y2,
    });
    updateAnnotation('rect', {
      id: id,
      type: 'rect',
      data: rect,
    });
  });

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    container.addEventListener('mousedown', handleMouseDown as any);
    container.addEventListener('mousemove', handleMouseMove as any);
    container.addEventListener('mouseup', handleMouseUp);
    container.addEventListener('mouseleave', handleMouseUp);

    return () => {
      container.removeEventListener('mousedown', handleMouseDown as any);
      container.removeEventListener('mousemove', handleMouseMove as any);
      container.removeEventListener('mouseup', handleMouseUp);
      container.removeEventListener('mouseleave', handleMouseUp);
    };
  }, [containerRef.current]);

  const handleRectMouseEnter = (id: string) => {
    setHoveredRectId(id);
  };

  const handleRectMouseLeave = () => {
    setHoveredRectId(null);
  };

  const handleRectClick = (id: string, e: MouseEvent) => {
    e.stopPropagation();
    setSelectedRectId(id);
    const anno = queryAnnotation(id);
    if (anno)
      editorProps.onAnnotationSelected?.(anno);
  };

  const handleContainerClick = (e: MouseEvent) => {
    setSelectedRectId(null);
    setHoveredRectId(null);
    editorProps.onAnnotationSelected?.(null);
  };

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    container.addEventListener('click', handleContainerClick);
    return () => {
      container.removeEventListener('click', handleContainerClick);
    };
  }, [containerRef]);

  // 矩形框的颜色
  const getLineColor = (id: string) => {
    if (hoveredRectId === null)
      return "white";
    if (selectedRectId === id || hoveredRectId === id)
      return "white";
    return "rgba(255, 255, 255, 0.3)";
  };

  // 是否显示遮罩
  const shouldShowMask = () => {
    if (!editorProps.enableMask)
      return false;
    if (editorProps.annotations.length === 0)
      return false;
    if (selectedRectId === null && hoveredRectId === null)
      return true;
    if (selectedRectId === hoveredRectId)
      return false;
    if (selectedRectId !== null)
      return false;
    if (hoveredRectId !== null)
      return true;
    return false;
  };

  const renderAnnotationWithHover = (annotations?: Annotation[]) => {
    if (!annotations) return null;
    return annotations.map((anno) => (
      <RectBox
        key={anno.id}
        mode={selectedRectId === anno.id ? "resize" : "move"}
        rect={Convertor.rectImage2Container(anno.data)}
        lineColor={getLineColor(anno.id)}
        onNativeMouseEnter={() => handleRectMouseEnter(anno.id)}
        onNativeMouseMove={handleMouseMove}    
        onNativeMouseLeave={handleRectMouseLeave}
        onNativeClick={(e) => handleRectClick(anno.id, e)}
        onTransform={(points) => handleRectTransform(points, anno.id)}
        rectTip={anno._tip}
        showRectTip={hoveredRectId === anno.id && selectedRectId === null}
      />
    ));
  };

  let rectMask;
  if (hoveredRectId !== null) {
    const rect = queryAnnotation(hoveredRectId);
    if (rect) {
      rectMask = (
        <RectMask
          rects={[{...rect.data}]}
          alpha={shouldShowMask() ? 0.7 : 0}
          transition={true}
          scale={state.imageScale}
          transform={{
            x: state.imagePosition.x,
            y: state.imagePosition.y,
            width: editorProps.imageSize?.width || 0,
            height: editorProps.imageSize?.height || 0
          }}
        />
      );
    }
  } else {
    rectMask = (
      <RectMask
        rects={editorProps.annotations?.map(anno => ({
          ...anno.data
        })) || []}
        alpha={shouldShowMask() ? editorProps.maskAlpha : 0}
        transition={true}
        scale={state.imageScale}
        transform={{
          x: state.imagePosition.x,
          y: state.imagePosition.y,
          width: editorProps.imageSize?.width || 0,
          height: editorProps.imageSize?.height || 0
        }}
      />
    );
  }

  return (
    <>
      {rectMask}
      {renderAnnotationWithHover(editorProps.annotations)}
    </>
  );
}

const DragTool: EditorTool = {
  name: 'drag',
  cursor: 'grab',
  Component: DragToolComponent
};

export default DragTool; 