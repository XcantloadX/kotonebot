import { ToolHandlerProps } from "./ImageEditor";
import RectMask from "./RectMask";
import { useState, useEffect } from "react";
import RectBox from "./RectBox";
import useLatestCallback from "../../hooks/useLatestCallback";
import { Annotation, RectPoints } from "./types";

function DragTool(props: ToolHandlerProps) {
    const { editorState, containerRef, editorProps, Convertor, updateAnnotation, queryAnnotation } = props;
    const [state, updateState] = editorState;
    const [hoveredRectId, setHoveredRectId] = useState<string | null>(null);
    const [selectedRectId, setSelectedRectId] = useState<string | null>(null);

    
    // 处理拖拽开始
    const handleMouseDown = useLatestCallback((e: React.MouseEvent) => {
        e.preventDefault();
        // 如果当前有选中的矩形，不启动图像拖拽
        if (selectedRectId !== null || hoveredRectId !== null) return;
        console.log('DragTool: handleMouseDown', 'selectedRectId=', selectedRectId, 'hoveredRectId=', hoveredRectId);
        
        updateState(draft => {
            draft.isDragging = true;
            draft.dragStart = {
                x: e.clientX - draft.imagePosition.x,
                y: e.clientY - draft.imagePosition.y,
            };
        });
    });

    // 处理拖拽过程
    const handleMouseMove = useLatestCallback((e: MouseEvent) => {
        if (!state.isDragging) return;
        const rect = containerRef.current?.getBoundingClientRect();
        if (!rect) return;
        console.log('DragTool: handleMouseMove', e);

        updateState(draft => {
            draft.imagePosition = {
                x: e.clientX - draft.dragStart.x,
                y: e.clientY - draft.dragStart.y,
            };

            draft.mousePosition = {
                x: e.clientX - rect.left,
                y: e.clientY - rect.top
            };
        });
    });

    // 处理拖拽结束
    const handleMouseUp = useLatestCallback(() => {
        updateState(draft => {
            draft.isDragging = false;
        });
    });

    // 处理矩形变换
    const handleRectTransform = useLatestCallback((rectPoints: RectPoints, id: string) => {
        console.log('DragTool: handleRectTransform');
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
        console.log('DragTool: handleRectMouseEnter', id);
        setHoveredRectId(id);
    };

    const handleRectMouseLeave = () => {
        console.log('DragTool: handleRectMouseLeave');
        setHoveredRectId(null);
    };

    // 点击矩形，选中矩形，矩形模式：move -> resize
    const handleRectClick = (id: string, e: MouseEvent) => {
        e.stopPropagation(); // 阻止事件冒泡到容器
        console.log('DragTool: handleRectClick', 'selectedRectId=', selectedRectId);
        setSelectedRectId(id);
        const anno = queryAnnotation(id);
        if (anno)
            editorProps.onAnnotationSelected?.(anno);
    };

    // 点击容器，取消选中
    const handleContainerClick = (e: MouseEvent) => {
        console.log('DragTool: handleContainerClick', 'selectedRectId=', selectedRectId, e);
        setSelectedRectId(null);
        setHoveredRectId(null);
        editorProps.onAnnotationSelected?.(null);
    };
    // 点击容器中的非矩形区域，取消选中当前矩形
    useEffect(() => {
        const container = containerRef.current;
        if (!container) return;


        container.addEventListener('click', handleContainerClick);
        return () => {
            container.removeEventListener('click', handleContainerClick);
        };
    }, [containerRef]);

    // 矩形框的颜色
    // 1. 没有 hover 任何矩形，所有矩形显示为白色
    // 2. hover 到某个矩形，该矩形显示为白色，其他矩形显示为半透明
    // 3. 选中某个矩形，该矩形显示为白色，其他矩形显示为半透明
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
        // 当有矩形被悬停时，只显示该矩形的遮罩
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
        // 默认显示所有矩形的遮罩
        rectMask = (
            <RectMask
                rects={editorProps.annotations?.map(anno => ({
                    // 获取图像坐标
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

export default DragTool;