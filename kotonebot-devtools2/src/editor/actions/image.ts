import { readText } from "../../api/fs";
import { messageBox } from "../../ui/messageBox";
import { useAppStore } from "../state";
import { requestHost, shouldUseSingleTabHostOpen } from "../host/hostBridge";
import i18n from "../../i18n";

const REQUEST_HOST_OPEN_META_DOCUMENT = "kotonebot.host.openMetaDocument";

interface OpenImageWithMetaOptions {
  allowHostDelegate?: boolean;
}

async function requestHostOpenMetaDocument(metaPath: string): Promise<void> {
  await requestHost(REQUEST_HOST_OPEN_META_DOCUMENT, { metaPath });
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
  if (data.version !== 2) {
    throw new Error(`Unsupported meta version: ${data.version}`);
  }
  setActiveMeta(path, data);
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
      if (data.version === 2) {
        setActiveMeta(path, data);
        continue;
      }
      const shouldStartFreshV2 = await messageBox.yes_no({
        title: i18n.t('image.legacyMetaFormat'),
        content: i18n.t('image.detectedLegacyFormat', { path: metaPath }),
        yesText: i18n.t('image.startFreshV2'),
        noText: i18n.t('dialog.cancel'),
        yesIntent: "warning",
      });
      if (shouldStartFreshV2) {
        setActiveMeta(path, { version: 2, definitions: {} });
      }
    } catch {
      setActiveMeta(path, { version: 2, definitions: {} });
    }
  }
}
