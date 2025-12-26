import { KonvaEventObject } from 'konva/lib/Node';
import { Vector2d } from 'konva/lib/types';
import { MetaV2, ResourceType } from '../../model/metaV2';
import { PrefabSchema } from '../../model/prefabSchema';

export interface ToolContext {
  activeMeta: { path: string; data: MetaV2 } | null;
  prefabSchema: PrefabSchema | null;
  activeResourceType: ResourceType;
  updateMeta: (updater: (draft: MetaV2) => void) => void;
  setSelection: (id: string | null) => void;
  setMode: (mode: any) => void;
  getRelativePointerPosition: () => Vector2d;
  scale: number;
  position: Vector2d;
  setPosition: (pos: Vector2d) => void;
}

export abstract class Tool {
  abstract onMouseDown(e: KonvaEventObject<MouseEvent>, ctx: ToolContext): void;
  abstract onMouseMove(e: KonvaEventObject<MouseEvent>, ctx: ToolContext): void;
  abstract onMouseUp(e: KonvaEventObject<MouseEvent>, ctx: ToolContext): void;
  onCancel(ctx: ToolContext): void {}
  onShapeClick(id: string, e: KonvaEventObject<MouseEvent>, ctx: ToolContext): void {}
  getPreview(): any { return null; }
  getCursor(): string { return 'default'; }
}
