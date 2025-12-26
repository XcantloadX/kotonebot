import React from 'react';
import { Circle, Group } from 'react-konva';
import { KonvaEventObject } from 'konva/lib/Node';

interface DefinitionPointProps {
  id: string;
  x: number;
  y: number;
  isSelected: boolean;
  scale: number;
  onClick: (id: string, e: KonvaEventObject<MouseEvent>) => void;
}

export const DefinitionPoint: React.FC<DefinitionPointProps> = React.memo(({
  id, x, y, isSelected, scale, onClick
}) => {
  return (
    <Group onClick={(e) => onClick(id, e)}>
      <Circle
          x={x}
          y={y}
          radius={5 / scale}
          fill={isSelected ? '#48aff0' : '#ff0000'}
          stroke="white"
          strokeWidth={1 / scale}
      />
    </Group>
  );
});
