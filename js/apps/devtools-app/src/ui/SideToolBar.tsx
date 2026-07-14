import React from 'react';
import { Button, Tooltip, Position, Divider, IconName, MaybeElement } from '@blueprintjs/core';

export interface Tool {
  id: string;
  icon: IconName | MaybeElement;
  title: string;
  onClick?: () => void;
  selectable?: boolean;
  /**
   * Custom render function for the tool button.
   * If provided, this function is responsible for rendering the tool.
   * The default button will not be rendered.
   */
  render?: (tool: Tool, isSelected: boolean) => React.ReactNode;
  disabled?: boolean;
  loading?: boolean;
}

export interface SideToolBarProps {
  tools: Array<Tool | 'separator'>;
  selectedToolId?: string;
  onSelectTool?: (id: string) => void;
  onClickTool?: (id: string) => void;
}

export const SideToolBar: React.FC<SideToolBarProps> = ({
  tools,
  selectedToolId,
  onSelectTool,
  onClickTool
}) => {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '4px', padding: '4px' }}>
      {tools.map((tool, index) => {
        if (tool === 'separator') {
          return <Divider key={`separator-${index}`} style={{ margin: '4px 0' }} />;
        }

        if (tool.render) {
            return <React.Fragment key={tool.id}>{tool.render(tool, selectedToolId === tool.id)}</React.Fragment>;
        }

        const handleClick = () => {
          tool.onClick?.();
          onClickTool?.(tool.id);
          if (tool.selectable !== false && onSelectTool) {
            onSelectTool(tool.id);
          }
        };

        return (
          <Tooltip content={tool.title} position={Position.RIGHT} key={tool.id}>
            <Button 
                icon={tool.icon} 
                active={tool.selectable !== false && selectedToolId === tool.id}
                onClick={handleClick}
                minimal
                large
                disabled={tool.disabled}
                loading={tool.loading}
                style={{ justifyContent: 'center' }}
            />
          </Tooltip>
        );
      })}
    </div>
  );
};
