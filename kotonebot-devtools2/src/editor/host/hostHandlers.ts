import { registerJumpToSymbolHandler } from "./handlers/jumpToSymbol";
import { registerOpenMetaDocumentHandler } from "./handlers/openMetaDocument";

export function registerHostHandlers(): () => void {
  const disposes = [registerOpenMetaDocumentHandler(), registerJumpToSymbolHandler()];
  return () => {
    for (const dispose of disposes) {
      dispose();
    }
  };
}
