import { ToolHandlerProps } from "./ImageEditor";
import { useEffect, useState, useRef } from "react";
import RectBox from "./RectBox";
import { Annotation, Point } from "./types";
import useLatestCallback from "../../hooks/useLatestCallback";
import { v4 } from "uuid";


function RectTool(props: ToolHandlerProps) {
    const { containerRef, addAnnotation, renderAnnotation, Convertor, editorProps } = props;
    // 下面两个都为容器坐标
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
            // const imagePos = Convertor.posContainer2Image({ x, y });
            setRectStart({ x, y });
            setRectEnd({ x, y });
        }
        drawingRef.current = true;
        console.log('RectTool: handleMouseDown');
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
        console.log('RectTool: handleMouseUp');
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
    }, [containerRef]);

    return (
        <>
            {rectStart && rectEnd && (
                <RectBox rect={{x1: rectStart.x, y1: rectStart.y, x2: rectEnd.x, y2: rectEnd.y}} />
            )}
            {renderAnnotation(editorProps.annotations, {
                mode: 'move',
                lineColor: drawingRef.current ? 'rgba(255, 255, 255, 0.3)' : 'white'
            })}
        </>
    );
}

export default RectTool;