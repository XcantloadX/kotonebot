/** Conversion 功能的行为层。 */

import { useAppStore } from "../state";
import { useConversionResultStore } from "../conversionResultStore";
import * as conversionApi from "../../api/conversion";
import { toaster } from "../../ui/toaster";
import { Intent } from "@blueprintjs/core";
import i18n from "../../i18n";

const POLL_INTERVAL = 500;
/** 当前活跃的轮询任务，用于在取消/切换时清理。 */
let activePollingTaskId: string | null = null;
let pollingAborted = false;

/** 启动异步扫描 + 轮询进度。
 *
 * 内部处理：打开 loading tab → 启动扫描 → 轮询 → 显示结果或错误。
 */
async function startScanAndPoll(
  tabLabel: string,
  request: conversionApi.ScanRequest,
) {
  const store = useConversionResultStore.getState();
  const appStore = useAppStore.getState();

  // 1. 立即打开 loading tab
  const id = `conversion-${Date.now()}`;
  store.setLoading();
  appStore.openTab({ id, kind: "conversion-result", label: tabLabel, closable: true });

  let taskId: string | null = null;
  try {
    // 2. 启动扫描
    const result = await conversionApi.startScan(request);
    taskId = result.taskId;
    store.setTaskId(taskId);
    activePollingTaskId = taskId;
    pollingAborted = false;

    // 3. 轮询进度
    while (!pollingAborted) {
      const progress = await conversionApi.fetchProgress(taskId);
      store.setProgress(progress);

      if (progress.state === "completed") {
        return;
      }
      if (progress.state === "cancelled") {
        store.setError(i18n.t("conversion.scanCancelled"));
        return;
      }
      if (progress.state === "error") {
        store.setError(progress.error || i18n.t("conversion.scanError"));
        return;
      }
      await sleep(POLL_INTERVAL);
    }
  } catch (err: any) {
    // 只有非主动取消的错误才显示
    if (!pollingAborted) {
      store.setError(err.message || i18n.t("conversion.scanError"));
    }
  } finally {
    if (taskId && activePollingTaskId === taskId) {
      activePollingTaskId = null;
    }
  }
}

function sleep(ms: number): Promise<void> {
  return new Promise((r) => setTimeout(r, ms));
}

/** 扫描所有文档。 */
export async function scanAllDocuments() {
  return startScanAndPoll(i18n.t("conversion.scanAllTab"), { mode: "all" });
}

/** 使用用户选择的图片路径进行扫描。 */
export async function scanWithImages(imagePaths: string[]) {
  return startScanAndPoll(i18n.t("conversion.scanSpecificTab"), {
    mode: "files",
    imagePaths,
  });
}

/** 使用设备截图进行扫描。 */
export async function scanWithScreenshot(screenshotPath: string) {
  return startScanAndPoll(i18n.t("conversion.scanDeviceTab"), {
    mode: "device",
    screenshotPath,
  });
}

/** 扫描当前文档（只匹配当前打开的 single 文档）。 */
export async function scanCurrentDocument(imagePath: string) {
  return startScanAndPoll(i18n.t("conversion.scanCurrentTab"), {
    mode: "current",
    singleImagePath: imagePath,
  });
}

/** 取消当前扫描。 */
export async function cancelScan() {
  const store = useConversionResultStore.getState();
  const taskId = store.taskId;
  if (!taskId) return;

  pollingAborted = true;
  activePollingTaskId = null;

  try {
    await conversionApi.cancelScan(taskId);
  } catch {
    // 忽略取消请求本身的错误
  }
  store.setError(i18n.t("conversion.scanCancelled"));
}

/** 执行转换：选中的匹配写入 multi 文档，删除 single 文档。 */
export async function executeConversion() {
  const store = useConversionResultStore.getState();
  const selected = store.getSelected();
  if (selected.length === 0) {
    toaster.show({ message: i18n.t("conversion.noSelection"), intent: Intent.WARNING, timeout: 3000 });
    return;
  }
  const singlePaths = selected.map(m => m.singleImagePath);
  if (new Set(singlePaths).size !== singlePaths.length) {
    toaster.show({ message: i18n.t("conversion.duplicateSingle"), intent: Intent.DANGER, timeout: 5000 });
    return;
  }
  const executeMatches: conversionApi.ConfirmedMatch[] = selected.map((m) => ({
    singleMetaPath: m.singleMetaPath,
    singleImagePath: m.singleImagePath,
    matchedImagePath: m.matchedImagePath,
    matchX: m.matchX,
    matchY: m.matchY,
    matchW: m.matchW,
    matchH: m.matchH,
  }));
  const result = await conversionApi.executeConversion(executeMatches);
  toaster.show({
    message: i18n.t("conversion.executeDone", {
      modified: result.modifiedMetaPaths.length,
      deleted: result.deletedSingleImagePaths.length,
    }),
    intent: Intent.SUCCESS,
    timeout: 5000,
  });
  return result;
}
