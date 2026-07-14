import { fetchJson } from "./client";
import { PrefabSchema } from "../model/prefabSchema";

export async function getPrefabSchema(): Promise<PrefabSchema> {
  return fetchJson<PrefabSchema>("/api/prefabs/schema");
}
