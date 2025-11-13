import { useState, useCallback } from 'react';
import { DRAG_TOOL_ID } from '../components/ToolBar/DynamicToolBar';

export function useToolManager() {
    const [currentTool, setCurrentTool] = useState<string>(DRAG_TOOL_ID);

    const selectTool = useCallback((id: string) => {
        setCurrentTool(id);
    }, []);

    return {
        currentTool,
        selectTool,
        setCurrentTool, // expose setter for hotkeys
    };
}
