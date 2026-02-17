import { readText } from "../../api/fs";
import { MessageBoxApi } from "../../ui/messageBox";
import { useAppStore } from "../state";

async function loadImage(path: string): Promise<{ width: number; height: number }> {
  const img = new Image();
  img.src = `/api/image?path=${encodeURIComponent(path)}`;
  await new Promise<void>((resolve, reject) => {
    img.onload = () => resolve();
    img.onerror = () => reject(new Error(`Failed to load image: ${path}`));
  });
  return { width: img.width, height: img.height };
}

export async function openImageWithMeta(path: string): Promise<void> {
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

export async function openImagesWithChecks(paths: string[], messageBox: MessageBoxApi): Promise<void> {
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
        title: "Legacy Meta Format",
        content: `Detected legacy or unknown meta format:\n${metaPath}\n\nStart fresh with V2 definitions?`,
        yesText: "Start Fresh V2",
        noText: "Cancel",
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
