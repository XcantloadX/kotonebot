import { openStrict } from "./image";

export async function openNewDocumentFromPath(imagePath: string): Promise<void> {
  await openStrict(imagePath, { source: "other" });
}