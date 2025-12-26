import { Tool, ToolContext } from './Tool';
import { KonvaEventObject } from 'konva/lib/Node';
import { Vector2d } from 'konva/lib/types';
import { v4 as uuidv4 } from 'uuid';

export class CreatingPrefabTool extends Tool {
  private startPos: Vector2d | null = null;
  private currentPos: Vector2d | null = null;
  private isDrawing = false;

  constructor(private prefab_id: string, private propKey: string, private toolType: "rect" | "point" | "image") {
    super();
  }

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

    // Don't create if too small (for rects)
    if ((this.toolType === 'rect' || this.toolType === 'image') && (Math.abs(x2 - x1) < 2 || Math.abs(y2 - y1) < 2)) {
        this.startPos = null;
        this.currentPos = null;
        return;
    }

    if (!ctx.prefabSchema) return;
    const schema = ctx.prefabSchema.prefabs[this.prefab_id];
    if (!schema) return;

    const id = uuidv4();
    const newDef: any = {
        type: 'prefab',
        prefab_id: this.prefab_id,
        name: schema.name,
        props: {}
    };

    // Do not fill props with default values except the primary prop
    const primaryProp = this.propKey;
    if (primaryProp && schema.props[primaryProp] && schema.props[primaryProp].default_value !== undefined) {
        newDef.props[primaryProp] = schema.props[primaryProp].default_value;
    }

    // Set the drawn property
    if (this.toolType === 'rect' || this.toolType === 'image') {
        newDef.props[this.propKey] = {
            kind: this.toolType,
            x1, y1, x2, y2
        };
    } else if (this.toolType === 'point') {
        newDef.props[this.propKey] = {
            kind: 'point',
            x: this.currentPos.x,
            y: this.currentPos.y
        };
    }

    ctx.updateMeta(draft => {
        draft.definitions[id] = newDef;
    });
    ctx.setSelection(id);
    ctx.setMode({ kind: 'idle' });
    
    this.startPos = null;
    this.currentPos = null;
  }
  
  getPreview() {
      if (!this.isDrawing || !this.startPos || !this.currentPos) return null;
      
      if (this.toolType === 'point') {
          return {
              kind: 'point',
              x: this.currentPos.x,
              y: this.currentPos.y
          };
      } else {
          return {
              kind: 'rect',
              x: Math.min(this.startPos.x, this.currentPos.x),
              y: Math.min(this.startPos.y, this.currentPos.y),
              width: Math.abs(this.currentPos.x - this.startPos.x),
              height: Math.abs(this.currentPos.y - this.startPos.y)
          };
      }
  }

  getCursor() { return 'crosshair'; }
}
