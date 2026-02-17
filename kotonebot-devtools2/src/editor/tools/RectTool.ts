import { Tool, ToolContext } from './Tool';
import { KonvaEventObject } from 'konva/lib/Node';
import { Vector2d } from 'konva/lib/types';
import { v4 as uuidv4 } from 'uuid';

export class RectTool extends Tool {
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
    if (!this.isDrawing || !this.startPos || !this.currentPos) return;
    this.isDrawing = false;

    const x1 = Math.min(this.startPos.x, this.currentPos.x);
    const y1 = Math.min(this.startPos.y, this.currentPos.y);
    const x2 = Math.max(this.startPos.x, this.currentPos.x);
    const y2 = Math.max(this.startPos.y, this.currentPos.y);

    // Don't create if too small
    if (Math.abs(x2 - x1) < 2 || Math.abs(y2 - y1) < 2) {
        this.startPos = null;
        this.currentPos = null;
        return;
    }

    const id = uuidv4();
    ctx.updateMeta(draft => {
        const props: any = {};
        if (ctx.activeResourceType === 'template') {
            props.image = { kind: 'image', x1, y1, x2, y2 };
        } else {
            props.rect = { kind: 'rect', x1, y1, x2, y2 };
        }

        draft.definitions[id] = {
            type: ctx.activeResourceType,
            props
        };
    }, { label: "Create rectangle definition", forceNewEntry: true });
    ctx.setSelection(id);
    
    this.startPos = null;
    this.currentPos = null;
  }
  
  getPreview() {
      if (!this.isDrawing || !this.startPos || !this.currentPos) return null;
      return {
          kind: 'rect',
          x: Math.min(this.startPos.x, this.currentPos.x),
          y: Math.min(this.startPos.y, this.currentPos.y),
          width: Math.abs(this.currentPos.x - this.startPos.x),
          height: Math.abs(this.currentPos.y - this.startPos.y)
      };
  }

  getCursor() { return 'crosshair'; }
}
