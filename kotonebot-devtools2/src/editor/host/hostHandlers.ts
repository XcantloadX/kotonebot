import { registerJumpToSymbolHandler } from "./handlers/jumpToSymbol";
import { registerOpenMetaDocumentHandler } from "./handlers/openMetaDocument";
import { registerRunEditorCommandHandler } from "./handlers/runEditorCommand";

export function registerHostHandlers(): () => void {
  const disposes = [registerOpenMetaDocumentHandler(), registerJumpToSymbolHandler(), registerRunEditorCommandHandler()];
  return () => {
    for (const dispose of disposes) {
      dispose();
    }
  };
}
