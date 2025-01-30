export enum Tool {
    Drag = 'drag',
    Rect = 'rect',
}

/** 标注类型。 */
export type AnnotationType = 'rect';

type AnnotationTypeMap = {
    rect: RectPoints,
};

export interface Annotation{
    id: string;
    type: AnnotationType;
    data: AnnotationTypeMap[AnnotationType];
}
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