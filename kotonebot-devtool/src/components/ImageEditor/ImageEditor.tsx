import React, { useRef, useEffect } from 'react';
import styled from '@emotion/styled';
import { Updater, useImmer } from 'use-immer';
import RectTool from './RectTool';
import DragTool from './DragTool';
import { Tool, Point, RectPoints, Annotation, AnnotationType } from './types';
import RectBox from './RectBox';
import NativeDiv from '../NativeDiv';

const EditorContainer = styled(NativeDiv)<{ isDragging: boolean }>`
  width: 100%;
  height: 100%;
  position: relative;
  overflow: hidden;
  background: #f0f0f0;
  user-select: none;
  cursor: ${props => props.isDragging ? 'grabbing' : 'grab'};
`;

const EditorImage = styled.img<{ scale: number; x: number; y: number }>`
  image-rendering: pixelated;
  position: absolute;
  transform: translate(${props => props.x}px, ${props => props.y}px) scale(${props => props.scale});
  transform-origin: left top;
  pointer-events: none;
`;

const CrosshairLine = styled(NativeDiv)<{ isVertical?: boolean; position: number }>`
  position: absolute;
  background-color: rgba(255, 255, 255, 0);
  border: none;
  ${props => props.isVertical
    ? `
      height: 100%;
      width: 0;
      left: ${props.position}px;
      border-left: 2px dashed rgba(255, 255, 255, 1);
    `
    : `
      width: 100%;
      height: 0;
      top: ${props.position}px;
      border-top: 2px dashed rgba(255, 255, 255, 1);
    `
  }
  pointer-events: none;
`;

export type AnnotationChangeType = 'add' | 'remove' | 'update';
export interface AnnotationChangedEvent {
  currentTool: Tool;
  type: AnnotationChangeType;
  annotationType: AnnotationType;
  annotation: Annotation;
}

export interface ImageEditorProps {
  image: string;
  tool?: Tool;
  initialScale?: number;
  showCrosshair?: boolean;
  annotations: Annotation[];
  onAnnotationChanged?: (e: AnnotationChangedEvent) => void;
  enableMask?: boolean;
  maskAlpha?: number;
}

export interface ImageEditorRef {
  reset: () => void;
  setScale: (scale: number) => void;
  getScale: () => number;
}

export interface EditorState {
  scale: number;
  position: Point;
  isDragging: boolean;
  dragStart: Point;
  mousePosition: Point;
}

export interface PostionConvertor {
  posContainer2Image: (pos: Point) => Point;
  posImage2Container: (pos: Point) => Point;
  rectImage2Container: (rect: RectPoints) => RectPoints;
  rectContainer2Image: (rect: RectPoints) => RectPoints;
}

export interface ToolHandlerProps {
  editorState: [EditorState, Updater<EditorState>];
  editorProps: ImageEditorProps;
  containerRef: React.RefObject<HTMLDivElement>;
  renderAnnotation: (annotations?: Annotation[]) => React.ReactNode;
  addAnnotation: (annotation: Annotation) => void;
  updateAnnotation: (type: AnnotationType, annotation: Annotation) => void;
  queryAnnotation: (id: string) => Annotation;
  Convertor: PostionConvertor;
}


const ImageEditor = React.forwardRef<ImageEditorRef, ImageEditorProps>((props, ref) => {
  const {
    image,
    initialScale = 1,
    showCrosshair = false,
    tool = Tool.Drag,
    onAnnotationChanged,
    annotations = [],
  } = props;

  const [state, updateState] = useImmer<EditorState>({
    scale: initialScale,
    position: { x: 0, y: 0 },
    isDragging: false,
    dragStart: { x: 0, y: 0 },
    mousePosition: { x: 0, y: 0 }
  });

  const containerRef = useRef<HTMLDivElement>(null);

  const Convertor = {
    /**
     * 从容器坐标转换到图片坐标
     * @param pos 容器坐标
     * @returns 图片坐标
     */
    posContainer2Image: (pos: Point) => {
      return {
        x: Math.round((pos.x - state.position.x) / state.scale),
        y: Math.round((pos.y - state.position.y) / state.scale)
      };
    },
    /**
     * 从图片坐标转换到容器坐标
     * @param pos 图片坐标
     * @returns 容器坐标
     */
    posImage2Container: (pos: Point) => {
      return {
        x: pos.x * state.scale + state.position.x,
        y: pos.y * state.scale + state.position.y
      };
    },
    /**
     * 从图片坐标转换到容器坐标
     * @param rect 图片坐标
     * @returns 容器坐标
     */
    rectImage2Container: (rect: RectPoints) => {
      return {
        x1: Convertor.posImage2Container({ x: rect.x1, y: rect.y1 }).x,
        y1: Convertor.posImage2Container({ x: rect.x1, y: rect.y1 }).y,
        x2: Convertor.posImage2Container({ x: rect.x2, y: rect.y2 }).x,
        y2: Convertor.posImage2Container({ x: rect.x2, y: rect.y2 }).y
      };
    },
    /**
     * 从容器坐标转换到图片坐标
     * @param rect 容器坐标
     * @returns 图片坐标
     */
    rectContainer2Image: (rect: RectPoints) => {
      return {
        x1: Convertor.posContainer2Image({ x: rect.x1, y: rect.y1 }).x,
        y1: Convertor.posContainer2Image({ x: rect.x1, y: rect.y1 }).y,
        x2: Convertor.posContainer2Image({ x: rect.x2, y: rect.y2 }).x,
        y2: Convertor.posContainer2Image({ x: rect.x2, y: rect.y2 }).y
      };
    }
  };

  const renderAnnotation = (annotations?: Annotation[]) => {
    if (!annotations) return null;
    return annotations.map((rect) => (
      <RectBox
        key={rect.id}
        mode="resize"
        rect={Convertor.rectImage2Container(rect.data)}
      />
    ));
  };
  const addAnnotation = (annotation: Annotation) => {
    console.log('Add annotation: ', annotation);
    onAnnotationChanged?.({
      currentTool: Tool.Rect,
      type: 'add',
      annotationType: 'rect',
      annotation: annotation
    });
  };
  const updateAnnotation = (type: AnnotationType, annotation: Annotation) => {
    console.log('Update rect: ', annotation);
    onAnnotationChanged?.({
      currentTool: Tool.Rect,
      type: 'update',
      annotationType: type,
      annotation: annotation
    });
  };

  const queryAnnotation = (id: string) => {
    let ret = null;
    if (annotations) {
      ret = annotations.find(annotation => annotation.id === id);
    }
    if (!ret)
      throw new Error(`Annotation not found: ${id}`);
    return ret;
  };
  
  const toolHandlerProps: ToolHandlerProps = {
    editorState: [state, updateState],
    editorProps: props,
    containerRef,
    addAnnotation,
    updateAnnotation,
    renderAnnotation,
    queryAnnotation,
    Convertor,
  };

  // 处理鼠标滚轮缩放
  const handleWheel = (e: WheelEvent) => {
    e.preventDefault();
    const delta = -e.deltaY;
    const scaleChange = delta > 0 ? 1.1 : 0.9;
    updateState(draft => {
      draft.scale = Math.max(0.1, Math.min(10, draft.scale * scaleChange));
    });
  };

  // 暴露组件方法
  React.useImperativeHandle(ref, () => ({
    reset: () => {
      updateState(draft => {
        draft.scale = initialScale;
        draft.position = { x: 0, y: 0 };
      });
    },
    setScale: (newScale: number) => {
      updateState(draft => {
        draft.scale = newScale;
      });
    },
    getScale: () => state.scale
  }));

  // 添加和移除滚轮事件监听器
  useEffect(() => {
    const container = containerRef.current;
    if (container) {
      container.addEventListener('wheel', handleWheel, { passive: false });
      return () => {
        container.removeEventListener('wheel', handleWheel);
      };
    }
  }, []);

  return (
    <EditorContainer
      ref={containerRef}
      isDragging={state.isDragging}
      style={{ cursor: tool === Tool.Rect ? 'crosshair' : undefined }}
    >
      <EditorImage
        src={image}
        scale={state.scale}
        x={state.position.x}
        y={state.position.y}
        draggable={false}
      />

      {showCrosshair && tool === Tool.Rect && (
        <>
          <CrosshairLine isVertical position={state.mousePosition.x} />
          <CrosshairLine position={state.mousePosition.y} />
        </>
      )}
      {tool === Tool.Rect && <RectTool {...toolHandlerProps} />}
      {tool === Tool.Drag && <DragTool {...toolHandlerProps} />}

    </EditorContainer>
  );
});
ImageEditor.displayName = 'ImageEditor';

export default ImageEditor;
