import { postForm } from "./client";
import { getImageUrl } from "./fs";
import type { components } from "./schema";

/** AI 路径建议响应。 */
export type SuggestPathResponse = components["schemas"]["SuggestPathResponse"];

/** AI 推断定义请求项。 */
export interface InferDefRequest {
  definitionId: string;
  templateRect?: { x1: number; y1: number; x2: number; y2: number };
}

/** AI 推断出的单条定义属性。 */
export interface InferDefResultItem {
  name: string;
  displayName: string;
  fixed: boolean;
  reason: string;
}

/** AI 推断定义结果，键为 definitionId。 */
export interface InferDefinitionsResult {
  definitions: Record<string, InferDefResultItem>;
}

export async function suggestDocumentPath(image: File): Promise<SuggestPathResponse> {
  const formData = new FormData();
  formData.set("image", image);

  const aiPrefs = (await import("../preferences/preferencesStore")).usePreferencesStore.getState().ai;
  formData.set("providerType", aiPrefs.providerType);
  formData.set("endpoint", aiPrefs.endpoint || "");
  formData.set("model", aiPrefs.model || "");
  formData.set("apiKey", aiPrefs.apiKey || "");

  return postForm<SuggestPathResponse>("/api/ai/suggest_path", formData);
}

export async function inferDefinitions(
  imagePath: string,
  definitions: InferDefRequest[],
): Promise<InferDefinitionsResult> {
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

  return postForm<InferDefinitionsResult>("/api/ai/infer_definitions", formData);
}
