import { readText } from "../../api/fs";
import { SymbolLite } from "../../model/symbolIndex";
import { useAppStore } from "../state";
import { useSymbolIndexStore } from "../symbolIndexStore";

export async function jumpToSymbol(symbol: SymbolLite): Promise<void> {
  const { documents, openDocument, setActiveDocument, setActiveMeta, setSelection, setViewState } = useAppStore.getState();

  const imagePath = symbol.imagePath;
  const metaPath = symbol.metaPath;

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
