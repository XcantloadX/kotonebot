import { readText } from "../../api/fs";
import { DiagnosticItem, SymbolLite } from "../../model/symbolIndex";
import { useAppStore } from "../state";
import { useSymbolIndexStore } from "../symbolIndexStore";
import { requestHost, shouldUseSingleTabHostOpen } from "../host/hostBridge";

const REQUEST_HOST_OPEN_META_DOCUMENT = "kotonebot.host.openMetaDocument";

async function requestHostOpenMetaDocument(metaPath: string): Promise<void> {
  await requestHost(REQUEST_HOST_OPEN_META_DOCUMENT, { metaPath });
}

async function ensureDocumentWithMeta(imagePath: string, metaPath: string): Promise<boolean> {
  const { documents, openDocument, setActiveDocument, setActiveMeta, activeDocumentId } = useAppStore.getState();
  if (shouldUseSingleTabHostOpen() && activeDocumentId !== null && activeDocumentId !== imagePath) {
    await requestHostOpenMetaDocument(metaPath);
    return false;
  }

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
  return true;
}

function normalizePath(path: string): string {
  return path.replace(/\\/g, "/").toLowerCase();
}

export async function jumpToSymbol(symbol: SymbolLite): Promise<void> {
  const { setSelection, setViewState, showFocusSpotlight } = useAppStore.getState();
  const imagePath = symbol.imagePath;
  const metaPath = symbol.metaPath;

  const ready = await ensureDocumentWithMeta(imagePath, metaPath);
  if (!ready) {
    return;
  }

  setSelection(symbol.definitionId);

  const geo = symbol.primaryGeometry;
  const nextDoc = useAppStore.getState().documents[imagePath];
  if (geo && nextDoc) {
    const center = geo.kind === "point"
      ? { x: geo.x, y: geo.y }
      : { x: (geo.x1 + geo.x2) / 2, y: (geo.y1 + geo.y2) / 2 };
    const scale = nextDoc.view?.scale || 1;
    const nextView = {
      x: -center.x * scale + nextDoc.image.width / 2,
      y: -center.y * scale + nextDoc.image.height / 2,
      scale,
    };

    // 展示 spotlight 动画，提示用户新视角的位置
    setViewState(imagePath, {
      x: nextView.x,
      y: nextView.y,
      scale: nextView.scale,
    });

    await new Promise<void>((resolve) => {
      window.requestAnimationFrame(() => resolve());
    });

    const stageContainer = document.getElementById("kb-editor-stage-container");
    if (!stageContainer) {
      throw new Error("Stage container not found");
    }
    const rect = stageContainer.getBoundingClientRect();
    const centerScreen = {
      x: rect.left + center.x * nextView.scale + nextView.x,
      y: rect.top + center.y * nextView.scale + nextView.y,
    };
    const radius = geo.kind === "point"
      ? 110
      : Math.max(
        110,
        Math.hypot((geo.x2 - geo.x1) * nextView.scale, (geo.y2 - geo.y1) * nextView.scale) / 2 + 40,
      );
    showFocusSpotlight({
      id: `${Date.now()}-${Math.random().toString(36).slice(2, 9)}`,
      centerScreen,
      radius,
      enterMs: 250,
      holdMs: 300,
      exitMs: 200,
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
  const ready = await ensureDocumentWithMeta(imagePath, diag.meta_path);
  if (!ready) {
    return;
  }
  const { setSelection } = useAppStore.getState();
  setSelection(diag.definition_id);
}
