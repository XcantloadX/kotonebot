export const Tool = {
    Drag: 'drag',
    Rect: 'rect',
    Point: 'point'
} as const;

export type Tool = typeof Tool[keyof typeof Tool];

/** 标注类型。 */
export type AnnotationType = 'rect' | 'point';


interface AnnotationBase {
    id: string;
    _tip?: React.ReactNode;
}

export type Annotation = 
  | (AnnotationBase & { type: 'rect'; data: RectPoints })
  | (AnnotationBase & { type: 'point'; data: Point });

export interface Point {
    x: number;
    y: number;
}

export interface RectPoints {
    x1: number;
    y1: number;
    x2: number;
    y2: number;
}

export interface AnnotationComponentProps {
    annotation: Annotation;
}

/**
 * 使对象中的所有属性都变为可选。
 */
export type Optional<T> = {
    [P in keyof T]?: T[P] | undefined;
};
