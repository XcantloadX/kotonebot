import { Tool, ToolContext } from './Tool';
import { KonvaEventObject } from 'konva/lib/Node';
import { Vector2d } from 'konva/lib/types';
import { v4 as uuidv4 } from 'uuid';

export class PointTool extends Tool {
  private startPos: Vector2d | null = null;
  private currentPos: Vector2d | null = null;
  private isDrawing = false;

  onMouseDown(e: KonvaEventObject<MouseEvent>, ctx: ToolContext) {
    const pos = ctx.getRelativePointerPosition();
    this.startPos = pos;
    this.currentPos = pos;
    this.isDrawing = true;
  }

  onMouseMove(e: KonvaEventObject<MouseEvent>, ctx: ToolContext) {
    if (!this.isDrawing) return;
    this.currentPos = ctx.getRelativePointerPosition();
  }

  onMouseUp(e: KonvaEventObject<MouseEvent>, ctx: ToolContext) {
    if (!this.isDrawing || !this.currentPos) return;
    this.isDrawing = false;

    const id = uuidv4();
    ctx.updateMeta(draft => {
        draft.definitions[id] = {
            type: 'hint-point',
            name: null,
            props: {
                point: { kind: 'point', x: this.currentPos!.x, y: this.currentPos!.y }
            }
        };
    }, { label: "Create point definition", forceNewEntry: true });
    ctx.setSelection(id);
    
    this.startPos = null;
    this.currentPos = null;
  }
  
  getPreview() {
      if (!this.isDrawing || !this.currentPos) return null;
      return {
          kind: 'point',
          x: this.currentPos.x,
          y: this.currentPos.y
      };
  }

  getCursor() { return 'crosshair'; }
}
