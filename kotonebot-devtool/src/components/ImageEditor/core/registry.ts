import { EditorTool, EditorOverlay } from './types';

class Registry {
  private tools = new Map<string, EditorTool>();
  private overlays = new Map<string, EditorOverlay>();

  registerTool(tool: EditorTool) {
    this.tools.set(tool.name, tool);
  }

  getTool(name: string) {
    return this.tools.get(name);
  }

  registerOverlay(overlay: EditorOverlay) {
    this.overlays.set(overlay.name, overlay);
  }

  getOverlays() {
    return Array.from(this.overlays.values())
      .sort((a, b) => a.zIndex - b.zIndex);
  }
}

export const registry = new Registry(); 