import { copyFile, readText, uploadFile } from "../../api/fs";
import { messageBox } from "../../ui/messageBox";
import { toaster } from "../../ui/toaster";
import { useAppStore } from "../state";
import { getActiveDocumentId } from "../commands/selectors";
import { requestHost, shouldUseSingleTabHostOpen } from "../host/hostBridge";
import { useRecentOpenStore, RecentOpenSource } from "../recentOpenStore";
import i18n from "../../i18n";

/** 替换当前文档图片的来源，可以是服务端已有路径，也可以是本地 File 对象（拖拽/粘贴）。 */
export type ReplaceImageSource =
  | { kind: "path"; path: string }
  | { kind: "file"; file: File; objectUrl: string };

const REQUEST_HOST_OPEN_META_DOCUMENT = "kotonebot.host.openMetaDocument";

/** 打开图片文档时的 meta 处理策略。 */
export type OpenStrategy = "strict" | "recover";

/** 打开图片文档的可选参数（不含策略，策略由具体入口决定）。 */
export interface OpenOptions {
  /** 是否允许在单标签 host 模式下委托给 host 打开。默认关闭。 */
  allowHostDelegate?: boolean;
  /** 最近打开记录来源标记。 */
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

/** 打开图片文档的核心实现，按策略处理 meta。
 *
 * @param paths - 待打开的图片路径列表
 * @param strategy - meta 处理策略：strict 对非 v3 meta 抛错；recover 对旧版/损坏 meta 弹窗询问或静默重建
 * @param options - 打开选项
 */
async function openWithStrategy(paths: string[], strategy: OpenStrategy, options?: OpenOptions): Promise<void> {
  const { openDocument, setActiveMeta } = useAppStore.getState();
  const source = options?.source ?? "file-dialog";
  for (const path of paths) {
    if (options?.allowHostDelegate === true && shouldUseSingleTabHostOpen()) {
      const activeId = getActiveDocumentId();
      if (activeId !== path) {
        await requestHostOpenMetaDocument(`${path}.json`);
        continue;
      }
    }
    const image = await loadImage(path);
    openDocument(path, image.width, image.height);

    const metaPath = `${path}.json`;
    if (strategy === "strict") {
      const content = await readText(metaPath);
      const data = JSON.parse(content);
      if (data.version !== 3) {
        throw new Error(`Unsupported meta version: ${data.version}`);
      }
      setActiveMeta(path, data);
      await trackRecentOpen(path, source);
      continue;
    }
    try {
      const content = await readText(metaPath);
      const data = JSON.parse(content);
      if (data.version === 3) {
        setActiveMeta(path, data);
        await trackRecentOpen(path, source);
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
        await trackRecentOpen(path, source);
      }
    } catch {
      setActiveMeta(path, { version: 3, definitions: {} });
      await trackRecentOpen(path, source);
    }
  }
}

/** 高级：用户触发打开（文件对话框/命令面板/最近打开），批量 + 容错恢复 meta。
 *
 * @param paths - 待打开的图片路径列表
 * @param options - 打开选项
 */
export async function open(paths: string[], options?: OpenOptions): Promise<void> {
  await openWithStrategy(paths, "recover", options);
}

/** 低级：程序化打开单个已知文档，严格校验 meta。
 *
 * @param path - 待打开的图片路径
 * @param options - 打开选项
 */
export async function openStrict(path: string, options?: OpenOptions): Promise<void> {
  await openWithStrategy([path], "strict", options);
}

export async function replaceActiveDocumentImage(source: ReplaceImageSource): Promise<void> {
  const activeDocId = getActiveDocumentId();
  if (!activeDocId) {
    throw new Error("No active document");
  }
  const { documents, refreshDocumentImage } = useAppStore.getState();
  const activeDoc = documents[activeDocId];
  if (!activeDoc) {
    throw new Error("No active document");
  }
  const currentPath = activeDoc.image.path;

  if (source.kind === "path") {
    await copyFile(source.path, currentPath);
  } else {
    await uploadFile(currentPath, source.file);
  }

  refreshDocumentImage(activeDocId);
  toaster.show({ message: i18n.t("image.replaced"), intent: "success" });
}
