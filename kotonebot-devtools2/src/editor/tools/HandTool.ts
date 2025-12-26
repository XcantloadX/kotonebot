import { Tool, ToolContext } from './Tool';
import { KonvaEventObject } from 'konva/lib/Node';
import { Vector2d } from 'konva/lib/types';

export class HandTool extends Tool {
  private isDragging = false;
  private lastPos: Vector2d | null = null;

  onMouseDown(e: KonvaEventObject<MouseEvent>, ctx: ToolContext) {
      this.isDragging = true;
      this.lastPos = { x: e.evt.clientX, y: e.evt.clientY };
  }

  onMouseMove(e: KonvaEventObject<MouseEvent>, ctx: ToolContext) {
      if (!this.isDragging || !this.lastPos) return;
      
      const dx = e.evt.clientX - this.lastPos.x;
      const dy = e.evt.clientY - this.lastPos.y;
      
      ctx.setPosition({
          x: ctx.position.x + dx,
          y: ctx.position.y + dy
      });
      
      this.lastPos = { x: e.evt.clientX, y: e.evt.clientY };
  }

  onMouseUp(e: KonvaEventObject<MouseEvent>, ctx: ToolContext) {
      this.isDragging = false;
      this.lastPos = null;
  }
  
  getCursor() { return this.isDragging ? 'grabbing' : 'grab'; }
}
