import { registerJumpToSymbolHandler } from "./handlers/jumpToSymbol";

export function registerHostHandlers(): () => void {
  const disposes = [registerJumpToSymbolHandler()];
  return () => {
    for (const dispose of disposes) {
      dispose();
    }
  };
}
