import { ToolHandler } from './ImageEditor/ImageEditor';
import { Rect } from './ImageEditor/ImageEditor';

export const useDragTool : ToolHandler = (args) => {
  const { editorState } = args;
  const [state, updateState] = editorState;

  const handleMouseDown = (e: React.MouseEvent) => {
    e.preventDefault();
    updateState(draft => {
      draft.isDragging = true;
      draft.dragStart = {
        x: e.clientX - draft.position.x,
        y: e.clientY - draft.position.y
      };
    });
  };

  const handleMouseMove = (e: React.MouseEvent) => {
    if (!state.isDragging) return;

    updateState(draft => {
      draft.position = {
        x: e.clientX - draft.dragStart.x,
        y: e.clientY - draft.dragStart.y
      };
    });
  };

  const handleMouseUp = () => {
    updateState(draft => {
      draft.isDragging = false;
    });
  };

  return {
    handleMouseDown,
    handleMouseMove,
    handleMouseUp
  };
};

export const useRectTool : ToolHandler = (args) => {
  const { editorState, containerRef, onAnnotationChange } = args;
  const [state, updateState] = editorState;

  const handleMouseDown = (e: React.MouseEvent) => {
    e.preventDefault();
    const rect = containerRef.current?.getBoundingClientRect();
    if (!rect) return;

    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    updateState(draft => {
      draft.rectStart = { x, y };
      draft.rectEnd = { x, y };
    });
  };

  const handleMouseMove = (e: React.MouseEvent) => {
    const rect = containerRef.current?.getBoundingClientRect();
    if (!rect) return;

    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;

    updateState(draft => {
      draft.mousePosition = { x, y };
      
      if (draft.rectStart) {
        draft.rectEnd = { x, y };
      }
    });
  };

  const handleMouseUp = () => {
    if (state.rectStart && state.rectEnd) {
      const newRect: Rect = {
        x: Math.min(state.rectStart.x, state.rectEnd.x),
        y: Math.min(state.rectStart.y, state.rectEnd.y),
        width: Math.abs(state.rectEnd.x - state.rectStart.x),
        height: Math.abs(state.rectEnd.y - state.rectStart.y)
      };

      updateState(draft => {
        draft.savedRects.push(newRect);
        draft.rectStart = null;
        draft.rectEnd = null;
      });

      onAnnotationChange?.({ rects: [...state.savedRects, newRect] });
    }
  };

  return {
    handleMouseDown,
    handleMouseMove,
    handleMouseUp
  };
}; 