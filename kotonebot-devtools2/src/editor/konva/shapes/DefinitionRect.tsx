import React from 'react';
import { Rect, Text, Group, Circle } from 'react-konva';
import { KonvaEventObject } from 'konva/lib/Node';

interface DefinitionRectProps {
  id: string;
  x1: number;
  y1: number;
  x2: number;
  y2: number;
  kind: 'rect' | 'image';
  label: string;
  isSelected: boolean;
  scale: number;
  onClick: (id: string, e: KonvaEventObject<MouseEvent>) => void;
  propKey?: string;
  onResizeStart?: (id: string, propKey: string | undefined) => void;
  onResize?: (id: string, propKey: string | undefined, rect: { x1: number; y1: number; x2: number; y2: number }) => void;
  onResizeEnd?: (id: string, propKey: string | undefined) => void;
}

export const DefinitionRect: React.FC<DefinitionRectProps> = React.memo(({
  id, x1, y1, x2, y2, kind, label, isSelected, scale, onClick, propKey, onResizeStart, onResize, onResizeEnd
}) => {
  const [hovered, setHovered] = React.useState(false);
  const handleSize = 8 / Math.max(1, scale);

  const handleDragStart = () => {
    onResizeStart?.(id, propKey);
  };

  const handleDragEndCommon = () => {
    onResizeEnd?.(id, propKey);
  };

  const handleDragEnd = (corner: 'tl'|'tr'|'bl'|'br') => (e: KonvaEventObject<any>) => {
    const pos = e.target.position();
    let nx1 = x1, ny1 = y1, nx2 = x2, ny2 = y2;
    if (corner === 'tl') { nx1 = pos.x; ny1 = pos.y; }
    if (corner === 'tr') { nx2 = pos.x; ny1 = pos.y; }
    if (corner === 'bl') { nx1 = pos.x; ny2 = pos.y; }
    if (corner === 'br') { nx2 = pos.x; ny2 = pos.y; }

    const newX1 = Math.min(nx1, nx2);
    const newX2 = Math.max(nx1, nx2);
    const newY1 = Math.min(ny1, ny2);
    const newY2 = Math.max(ny1, ny2);

    onResize?.(id, propKey, { x1: newX1, y1: newY1, x2: newX2, y2: newY2 });
    handleDragEndCommon();
  };
  const handleDragMove = (corner: 'tl'|'tr'|'bl'|'br') => (e: KonvaEventObject<any>) => {
    const pos = e.target.position();
    let nx1 = x1, ny1 = y1, nx2 = x2, ny2 = y2;
    if (corner === 'tl') { nx1 = pos.x; ny1 = pos.y; }
    if (corner === 'tr') { nx2 = pos.x; ny1 = pos.y; }
    if (corner === 'bl') { nx1 = pos.x; ny2 = pos.y; }
    if (corner === 'br') { nx2 = pos.x; ny2 = pos.y; }

    const newX1 = Math.min(nx1, nx2);
    const newX2 = Math.max(nx1, nx2);
    const newY1 = Math.min(ny1, ny2);
    const newY2 = Math.max(ny1, ny2);

    onResize?.(id, propKey, { x1: newX1, y1: newY1, x2: newX2, y2: newY2 });
  };
  const handleRectDragMove = (e: KonvaEventObject<any>) => {
    const node = e.target;
    const nx = node.x();
    const ny = node.y();
    const w = x2 - x1;
    const h = y2 - y1;
    const newX1 = nx;
    const newY1 = ny;
    const newX2 = nx + w;
    const newY2 = ny + h;
    onResize?.(id, propKey, { x1: newX1, y1: newY1, x2: newX2, y2: newY2 });
  };

  const handleEdgeDragMove = (edge: 'top'|'bottom'|'left'|'right') => (e: KonvaEventObject<any>) => {
    const pos = e.target.position();
    let nx1 = x1, ny1 = y1, nx2 = x2, ny2 = y2;
    if (edge === 'top') ny1 = pos.y;
    if (edge === 'bottom') ny2 = pos.y;
    if (edge === 'left') nx1 = pos.x;
    if (edge === 'right') nx2 = pos.x;

    const newX1 = Math.min(nx1, nx2);
    const newX2 = Math.max(nx1, nx2);
    const newY1 = Math.min(ny1, ny2);
    const newY2 = Math.max(ny1, ny2);

    onResize?.(id, propKey, { x1: newX1, y1: newY1, x2: newX2, y2: newY2 });
  };
  const setCursor = (e: KonvaEventObject<any>, cursor: string) => {
    const stage = e.target.getStage();
    if (stage) {
      const c = stage.container();
      if (c) c.style.cursor = cursor;
    }
  };
  const BLUE = '#48aff0';
  const BLUE_FILL = 'rgba(72, 175, 240, 0.36)';
  const ORANGE = '#ff7300';
  const ORANGE_FILL = 'rgba(255, 115, 0, 0.2)';
    return (
    <Group onClick={(e) => onClick(id, e)} onMouseEnter={() => setHovered(true)} onMouseLeave={() => setHovered(false)}>
      <Rect
          x={x1}
          y={y1}
          width={x2 - x1}
          height={y2 - y1}
          stroke={isSelected ? ORANGE : BLUE}
          strokeWidth={2 / scale}
          fill={isSelected ? ORANGE_FILL : BLUE_FILL}
          draggable={isSelected}
          onDragStart={isSelected ? handleDragStart : undefined}
          onDragMove={isSelected ? handleRectDragMove : undefined}
          onDragEnd={isSelected ? handleDragEndCommon : undefined}
      />
        {hovered && (
          <Text
            x={x1 ?? x1}
            y={y1 - 15 / scale}
            text={label}
            fill="#eee"
            fontFamily='consolas'
            fontSize={15 / scale}
            shadowColor="black"
            shadowBlur={1}
            strokeWidth={1 / scale}
            stroke="black"
            fillAfterStrokeEnabled
          />
        )}
      {isSelected && (
          <>
            {/* corner handles */}
            <Circle x={x1} y={y1} radius={handleSize} fill="#fff" stroke={ORANGE} strokeWidth={1/scale} draggable onDragStart={handleDragStart} onDragEnd={handleDragEnd('tl')} onDragMove={handleDragMove('tl')} onMouseEnter={e => setCursor(e, 'nwse-resize')} onMouseLeave={e => setCursor(e, '')} />
            <Circle x={x2} y={y1} radius={handleSize} fill="#fff" stroke={ORANGE} strokeWidth={1/scale} draggable onDragStart={handleDragStart} onDragEnd={handleDragEnd('tr')} onDragMove={handleDragMove('tr')} onMouseEnter={e => setCursor(e, 'nesw-resize')} onMouseLeave={e => setCursor(e, '')} />
            <Circle x={x1} y={y2} radius={handleSize} fill="#fff" stroke={ORANGE} strokeWidth={1/scale} draggable onDragStart={handleDragStart} onDragEnd={handleDragEnd('bl')} onDragMove={handleDragMove('bl')} onMouseEnter={e => setCursor(e, 'nesw-resize')} onMouseLeave={e => setCursor(e, '')} />
            <Circle x={x2} y={y2} radius={handleSize} fill="#fff" stroke={ORANGE} strokeWidth={1/scale} draggable onDragStart={handleDragStart} onDragEnd={handleDragEnd('br')} onDragMove={handleDragMove('br')} onMouseEnter={e => setCursor(e, 'nwse-resize')} onMouseLeave={e => setCursor(e, '')} />

            {/* edge handles */}
            <Circle x={(x1 + x2) / 2} y={y1} radius={handleSize} fill="#fff" stroke={ORANGE} strokeWidth={1/scale} draggable onDragStart={handleDragStart} onDragMove={handleEdgeDragMove('top')} onDragEnd={handleDragEndCommon} onMouseEnter={e => setCursor(e, 'ns-resize')} onMouseLeave={e => setCursor(e, '')} />
            <Circle x={(x1 + x2) / 2} y={y2} radius={handleSize} fill="#fff" stroke={ORANGE} strokeWidth={1/scale} draggable onDragStart={handleDragStart} onDragMove={handleEdgeDragMove('bottom')} onDragEnd={handleDragEndCommon} onMouseEnter={e => setCursor(e, 'ns-resize')} onMouseLeave={e => setCursor(e, '')} />
            <Circle x={x1} y={(y1 + y2) / 2} radius={handleSize} fill="#fff" stroke={ORANGE} strokeWidth={1/scale} draggable onDragStart={handleDragStart} onDragMove={handleEdgeDragMove('left')} onDragEnd={handleDragEndCommon} onMouseEnter={e => setCursor(e, 'ew-resize')} onMouseLeave={e => setCursor(e, '')} />
            <Circle x={x2} y={(y1 + y2) / 2} radius={handleSize} fill="#fff" stroke={ORANGE} strokeWidth={1/scale} draggable onDragStart={handleDragStart} onDragMove={handleEdgeDragMove('right')} onDragEnd={handleDragEndCommon} onMouseEnter={e => setCursor(e, 'ew-resize')} onMouseLeave={e => setCursor(e, '')} />
          </>
      )}
    </Group>
  );
});
