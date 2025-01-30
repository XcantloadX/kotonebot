import { ToolHandlerProps } from "./ImageEditor";
import { useEffect, useState } from "react";
import RectBox from "./RectBox";
import { Point } from "./types";
import useLatestCallback from "../../hooks/useLatestCallback";
import { v4 } from "uuid";


function RectTool(props: ToolHandlerProps) {
    const { containerRef, addAnnotation, renderAnnotation, Convertor, editorProps } = props;
    const [rectStart, setRectStart] = useState<Point | null>(null);
    const [rectEnd, setRectEnd] = useState<Point | null>(null);

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
        let newRect = { x1, y1, x2, y2 };
        // 转换到图片坐标
        newRect = Convertor.rectContainer2Image(newRect);
        
        addAnnotation({
            id: v4(),
            type: 'rect',
            data: newRect
        });
        setRectStart(null);
        setRectEnd(null);
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
            {renderAnnotation(editorProps.annotations)}
        </>
    );
}

export default RectTool;