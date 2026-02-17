import { Tool, ToolContext } from './Tool';
import { KonvaEventObject } from 'konva/lib/Node';
import { Vector2d } from 'konva/lib/types';

export class PickingTool extends Tool {
  private startPos: Vector2d | null = null;
  private currentPos: Vector2d | null = null;
  private isDrawing = false;

  constructor(private definitionId: string, private propKey: string, private toolType: "rect" | "point" | "image") {
    super();
  }

  getCursor() { return 'crosshair'; }

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

    ctx.updateMeta(draft => {
        const def = draft.definitions[this.definitionId];
        if (!def) return;

        if (this.toolType === 'rect' || this.toolType === 'image') {
            def.props[this.propKey] = {
                kind: this.toolType,
                x1, y1, x2, y2
            };
        } else if (this.toolType === 'point') {
            def.props[this.propKey] = {
                kind: 'point',
                x: this.currentPos!.x,
                y: this.currentPos!.y
            };
        }
    }, {
        label: `Pick ${this.toolType} for ${this.propKey}`,
        mergeKey: `pick:${this.definitionId}:${this.propKey}`,
        forceNewEntry: true,
    });
    ctx.setMode({ kind: 'idle' });
    
    this.startPos = null;
    this.currentPos = null;
  }
  
  getPreview() {
      if (!this.isDrawing || !this.startPos || !this.currentPos) return null;
      if (this.toolType === 'rect' || this.toolType === 'image') {
          return {
              kind: 'rect',
              x: Math.min(this.startPos.x, this.currentPos.x),
              y: Math.min(this.startPos.y, this.currentPos.y),
              width: Math.abs(this.currentPos.x - this.startPos.x),
              height: Math.abs(this.currentPos.y - this.startPos.y)
          };
      } else {
          return {
              kind: 'point',
              x: this.currentPos.x,
              y: this.currentPos.y
          };
      }
  }
}
