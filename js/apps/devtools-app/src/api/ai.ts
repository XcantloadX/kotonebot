import { fetchJson } from "./client";
import { getImageUrl } from "./fs";

export interface InferDefRequest {
  definitionId: string;
  templateRect?: { x1: number; y1: number; x2: number; y2: number };
}

export interface InferDefResultItem {
  name: string;
  displayName: string;
  fixed: boolean;
  reason: string;
}

export async function inferDefinitions(
  imagePath: string,
  definitions: InferDefRequest[],
): Promise<Record<string, InferDefResultItem>> {
  const imageParts = imagePath.replace(/\\/g, "/").split("/");
  const imageFilename = imageParts[imageParts.length - 1] || "screenshot.png";

  const imageResponse = await fetch(getImageUrl(imagePath));
  if (!imageResponse.ok) {
    throw new Error(`Failed to fetch image: ${imageResponse.status}`);
  }
  const imageBlob = await imageResponse.blob();
  const imageFile = new File([imageBlob], imageFilename, { type: imageBlob.type || "image/png" });

  const formData = new FormData();
  formData.set("image", imageFile);
  formData.set("definitionsJson", JSON.stringify(definitions));
  formData.set("imagePath", imagePath);

  const aiPrefs = (await import("../preferences/preferencesStore")).usePreferencesStore.getState().ai;
  formData.set("providerType", aiPrefs.providerType);
  formData.set("endpoint", aiPrefs.endpoint || "");
  formData.set("model", aiPrefs.model || "");
  formData.set("apiKey", aiPrefs.apiKey || "");

  return fetchJson<Record<string, InferDefResultItem>>("/api/ai/infer_definitions", {
    method: "POST",
    body: formData,
  });
}
