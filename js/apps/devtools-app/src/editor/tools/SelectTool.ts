import { Tool, ToolContext } from './Tool';
import { KonvaEventObject } from 'konva/lib/Node';

export class SelectTool extends Tool {
  onMouseDown() {}
  onMouseMove() {}
  onMouseUp() {}
  
  onShapeClick(id: string, e: KonvaEventObject<MouseEvent>, ctx: ToolContext) {
      e.cancelBubble = true;
      ctx.setSelection(id);
  }

  getCursor() { return 'default'; }
}
