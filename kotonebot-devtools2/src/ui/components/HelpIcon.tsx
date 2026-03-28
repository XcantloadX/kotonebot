import React from 'react';
import { Tooltip, Icon, Position } from '@blueprintjs/core';

interface HelpIconProps {
  content: string | React.ReactElement;
  size?: number;
  position?: Position;
  color?: string;
  tooltipProps?: Omit<React.ComponentProps<typeof Tooltip>, 'content' | 'position'>;
}

export const HelpIcon: React.FC<HelpIconProps> = ({
  content,
  size = 14,
  position = Position.RIGHT,
  color = '#2b6f9e',
  tooltipProps,
}) => {
  return (
    <Tooltip content={content} position={position} {...tooltipProps}>
      <span style={{ display: 'inline-flex', alignItems: 'center' }}>
        <Icon icon="help" size={size} style={{ color }} />
      </span>
    </Tooltip>
  );
};
