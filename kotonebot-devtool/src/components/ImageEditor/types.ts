export const Tool = {
    Drag: 'drag',
    Rect: 'rect',
} as const;

export type Tool = typeof Tool[keyof typeof Tool];

/** 标注类型。 */
export type AnnotationType = 'rect';

type AnnotationTypeMap = {
    rect: RectPoints,
};

export interface Annotation {
    id: string;
    type: AnnotationType;
    data: AnnotationTypeMap[AnnotationType];
    /** 提示信息。 */
    _tip?: React.ReactNode;
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

/**
 * 使对象中的所有属性都变为可选。
 */
export type Optional<T> = {
    [P in keyof T]?: T[P] | undefined;
};
