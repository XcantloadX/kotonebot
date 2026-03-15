import * as http from "node:http";
import * as https from "node:https";

export function requestBuffer(url: string): Promise<Buffer> {
  const parsed = new URL(url);
  const sender = parsed.protocol === "https:" ? https : http;
  return new Promise((resolve, reject) => {
    const req = sender.request(
      parsed,
      {
        method: "GET",
        timeout: 8000,
      },
      (res) => {
        const status = res.statusCode;
        if (status === undefined || status < 200 || status >= 300) {
          reject(new Error(`Request failed with status ${String(status)}: ${url}`));
          res.resume();
          return;
        }
        const chunks: Buffer[] = [];
        res.on("data", (chunk: Buffer) => {
          chunks.push(chunk);
        });
        res.on("end", () => {
          resolve(Buffer.concat(chunks));
        });
      },
    );
    req.on("timeout", () => {
      req.destroy(new Error(`Request timeout: ${url}`));
    });
    req.on("error", (err: Error) => {
      reject(err);
    });
    req.end();
  });
}

/** 请求并解析 JSON，返回 unknown 供上层做类型校验。 */
export async function requestJsonUnknown(url: string): Promise<unknown> {
  const content = await requestBuffer(url);
  return JSON.parse(content.toString("utf-8")) as unknown;
}
