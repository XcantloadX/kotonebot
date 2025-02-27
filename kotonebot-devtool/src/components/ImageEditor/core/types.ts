import { RefObject } from 'react';
import { EditorState, ImageEditorProps } from '../ImageEditor';
import { Annotation, AnnotationType, Point, RectPoints } from '../types';
import { Updater } from 'use-immer';

export interface ToolContext {
  editorState: [EditorState, Updater<EditorState>];
  containerRef: RefObject<HTMLDivElement>;
  imageSize: {
    width: number;
    height: number;
  };
  Convertor: {
    posContainer2Image: (pos: Point) => Point;
    posImage2Container: (pos: Point) => Point;
    rectImage2Container: (rect: RectPoints) => RectPoints;
    rectContainer2Image: (rect: RectPoints) => RectPoints;
  };
  updateAnnotation: (type: AnnotationType, annotation: Annotation) => void;
  addAnnotation: (annotation: Annotation) => void;
  queryAnnotation: (id: string) => Annotation | null | undefined;
  editorProps: ImageEditorProps;
}

export interface ToolProps extends ToolContext {
  // 工具特有的属性可以在这里添加
}

export type EditorTool = {
  name: string;
  cursor?: string;
  onActivate?: (ctx: ToolContext) => void;
  onDeactivate?: (ctx: ToolContext) => void;
  Component: React.FC<ToolProps>;
}

export interface OverlayProps extends ToolContext {
  tool: string;
}

export interface EditorOverlay {
  name: string;
  zIndex: number;
  component: React.FC<OverlayProps>;
} 