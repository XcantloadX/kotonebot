import React from 'react';
import { BsCursor, BsFolder2Open, BsFloppy } from 'react-icons/bs';
import { SideToolBar, Tool } from '../../../../components/SideToolBar';
import { toolRegistry } from '../../tools/registry';
import { Tool as EditorTool } from '../../../../components/ImageEditor/types';

interface DynamicToolBarProps {
    selectedToolId: string;
    onSelectTool: (id: string) => void;
    onClickTool: (id:string) => void;
}

export const DRAG_TOOL_ID = EditorTool.Drag;

const DynamicToolBar: React.FC<DynamicToolBarProps> = ({ selectedToolId, onSelectTool, onClickTool }) => {
    const staticTools: Array<Tool | 'separator'> = [
        {
            id: 'open',
            icon: <BsFolder2Open size={24} />,
            title: '打开',
            selectable: false,
        },
        {
            id: 'save',
            icon: <BsFloppy size={24} />,
            title: '保存',
            selectable: false,
        },
        'separator',
        {
            id: DRAG_TOOL_ID,
            icon: <BsCursor size={24} />,
            title: '拖动工具 (V)',
            selectable: true,
        },
    ];

    const pluginTools: Tool[] = toolRegistry.getAll().map(plugin => ({
        id: plugin.id,
        icon: plugin.icon,
        title: `${plugin.name} (${plugin.hotkey})`,
        selectable: true,
    }));

    const allTools = [...staticTools, ...pluginTools];

    return (
        <SideToolBar
            tools={allTools}
            selectedToolId={selectedToolId}
            onSelectTool={onSelectTool}
            onClickTool={onClickTool}
        />
    );
};

export default DynamicToolBar;
