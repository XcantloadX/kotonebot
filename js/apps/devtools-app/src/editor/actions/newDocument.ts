import { openImageWithMeta } from "./image";

export async function openNewDocumentFromPath(imagePath: string): Promise<void> {
  await openImageWithMeta(imagePath, { source: "other" });
}