import { copyFile, readText, uploadFile } from "../../api/fs";
import { messageBox } from "../../ui/messageBox";
import { toaster } from "../../ui/toaster";
import { useAppStore } from "../state";
import { requestHost, shouldUseSingleTabHostOpen } from "../host/hostBridge";
import { useRecentOpenStore, RecentOpenSource } from "../recentOpenStore";
import i18n from "../../i18n";

/** 替换当前文档图片的来源，可以是服务端已有路径，也可以是本地 File 对象（拖拽/粘贴）。 */
export type ReplaceImageSource =
  | { kind: "path"; path: string }
  | { kind: "file"; file: File; objectUrl: string };

const REQUEST_HOST_OPEN_META_DOCUMENT = "kotonebot.host.openMetaDocument";

interface OpenImageWithMetaOptions {
  allowHostDelegate?: boolean;
  source?: RecentOpenSource;
}

async function requestHostOpenMetaDocument(metaPath: string): Promise<void> {
  await requestHost(REQUEST_HOST_OPEN_META_DOCUMENT, { metaPath });
}

async function trackRecentOpen(imagePath: string, source: RecentOpenSource): Promise<void> {
  const recentStore = useRecentOpenStore.getState();
  recentStore.addRecent({
    imagePath,
    metaPath: `${imagePath}.json`,
    source,
  });
}

async function loadImage(path: string): Promise<{ width: number; height: number }> {
  const img = new Image();
  img.src = `/api/image?path=${encodeURIComponent(path)}`;
  await new Promise<void>((resolve, reject) => {
    img.onload = () => resolve();
    img.onerror = () => reject(new Error(`Failed to load image: ${path}`));
  });
  return { width: img.width, height: img.height };
}

export async function openImageWithMeta(path: string, options?: OpenImageWithMetaOptions): Promise<void> {
  const allowHostDelegate = options?.allowHostDelegate ?? true;
  const source = options?.source ?? "file-dialog";
  if (allowHostDelegate && shouldUseSingleTabHostOpen()) {
    const activeDocumentId = useAppStore.getState().activeDocumentId;
    if (activeDocumentId !== path) {
      await requestHostOpenMetaDocument(`${path}.json`);
      return;
    }
  }
  const { openDocument, setActiveMeta } = useAppStore.getState();
  const image = await loadImage(path);
  openDocument(path, image.width, image.height);

  const metaPath = `${path}.json`;
  const content = await readText(metaPath);
  const data = JSON.parse(content);
  if (data.version !== 3) {
    throw new Error(`Unsupported meta version: ${data.version}`);
  }
  setActiveMeta(path, data);
  await trackRecentOpen(path, source);
}

export async function replaceActiveDocumentImage(source: ReplaceImageSource): Promise<void> {
  const { activeDocumentId, documents, refreshDocumentImage } = useAppStore.getState();
  const activeDoc = activeDocumentId ? documents[activeDocumentId] : null;
  if (!activeDocumentId || !activeDoc) {
    throw new Error("No active document");
  }
  const currentPath = activeDoc.image.path;

  if (source.kind === "path") {
    await copyFile(source.path, currentPath);
  } else {
    await uploadFile(currentPath, source.file);
  }

  refreshDocumentImage(activeDocumentId);
  toaster.show({ message: i18n.t("image.replaced"), intent: "success" });
}

export async function openImagesWithChecks(paths: string[]): Promise<void> {
  const { openDocument, setActiveMeta } = useAppStore.getState();
  for (const path of paths) {
    const image = await loadImage(path);
    openDocument(path, image.width, image.height);

    const metaPath = `${path}.json`;
    try {
      const content = await readText(metaPath);
      const data = JSON.parse(content);
      if (data.version === 3) {
        setActiveMeta(path, data);
        await trackRecentOpen(path, "file-dialog");
        continue;
      }
      const shouldStartFreshV3 = await messageBox.yes_no({
        title: i18n.t('image.legacyMetaFormat'),
        content: i18n.t('image.detectedLegacyFormat', { path: metaPath }),
        yesText: i18n.t('image.startFreshV3'),
        noText: i18n.t('dialog.cancel'),
        yesIntent: "warning",
      });
      if (shouldStartFreshV3) {
        setActiveMeta(path, { version: 3, definitions: {} });
        await trackRecentOpen(path, "file-dialog");
      }
    } catch {
      setActiveMeta(path, { version: 3, definitions: {} });
      await trackRecentOpen(path, "file-dialog");
    }
  }
}
