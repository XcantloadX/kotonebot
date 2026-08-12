import { client, unwrap } from "./client";
import { PrefabSchema } from "../model/prefabSchema";

export async function getPrefabSchema(): Promise<PrefabSchema> {
  const result = await unwrap(client.GET("/api/prefabs/schema"));
  // 线格式 prefabs 为宽泛 Record<string, unknown>，收窄为编辑器使用的富 schema 类型
  return result as PrefabSchema;
}
