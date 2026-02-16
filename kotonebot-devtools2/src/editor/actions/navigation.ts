import { readText } from "../../api/fs";
import { DiagnosticItem, SymbolLite } from "../../model/symbolIndex";
import { useAppStore } from "../state";
import { useSymbolIndexStore } from "../symbolIndexStore";

async function ensureDocumentWithMeta(imagePath: string, metaPath: string): Promise<void> {
  const { documents, openDocument, setActiveDocument, setActiveMeta } = useAppStore.getState();

  let activeDoc = documents[imagePath];
  if (!activeDoc) {
    const img = new Image();
    img.src = `/api/image?path=${encodeURIComponent(imagePath)}`;
    await new Promise<void>((resolve, reject) => {
      img.onload = () => resolve();
      img.onerror = () => reject(new Error(`Failed to load image: ${imagePath}`));
    });
    openDocument(imagePath, img.width, img.height);
    activeDoc = useAppStore.getState().documents[imagePath];
  } else {
    setActiveDocument(imagePath);
  }

  if (!activeDoc?.meta || activeDoc.meta.path !== metaPath) {
    const content = await readText(metaPath);
    const data = JSON.parse(content);
    if (data.version !== 2) {
      throw new Error(`Unsupported meta version: ${data.version}`);
    }
    setActiveMeta(imagePath, data);
  }
}

function normalizePath(path: string): string {
  return path.replace(/\\/g, "/").toLowerCase();
}

export async function jumpToSymbol(symbol: SymbolLite): Promise<void> {
  const { setSelection, setViewState } = useAppStore.getState();
  const imagePath = symbol.imagePath;
  const metaPath = symbol.metaPath;

  await ensureDocumentWithMeta(imagePath, metaPath);

  setSelection(symbol.definitionId);

  const geo = symbol.primaryGeometry;
  const nextDoc = useAppStore.getState().documents[imagePath];
  if (geo && nextDoc) {
    const center = geo.kind === "point"
      ? { x: geo.x, y: geo.y }
      : { x: (geo.x1 + geo.x2) / 2, y: (geo.y1 + geo.y2) / 2 };
    const scale = nextDoc.view?.scale || 1;
    setViewState(imagePath, {
      x: -center.x * scale + nextDoc.image.width / 2,
      y: -center.y * scale + nextDoc.image.height / 2,
      scale,
    });
  }

  useSymbolIndexStore.getState().markUsed(symbol.symbolKey);
}

export async function jumpToDiagnostic(diag: DiagnosticItem): Promise<void> {
  const { symbols } = useSymbolIndexStore.getState();
  const hit = symbols.find((symbol) => {
    if (normalizePath(symbol.metaPath) !== normalizePath(diag.meta_path)) {
      return false;
    }
    if (diag.definition_id === null) {
      return false;
    }
    return symbol.definitionId === diag.definition_id;
  });
  if (hit) {
    await jumpToSymbol(hit);
    return;
  }

  const imagePath = diag.meta_path.endsWith(".json")
    ? diag.meta_path.slice(0, -".json".length)
    : diag.meta_path;
  await ensureDocumentWithMeta(imagePath, diag.meta_path);
  const { setSelection } = useAppStore.getState();
  setSelection(diag.definition_id);
}
