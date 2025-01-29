import { DebugRecord } from '../types/debug';

export const readJsonFile = async (file: File): Promise<DebugRecord[]> => {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = (event) => {
      try {
        const content = event.target?.result as string;
        const data = JSON.parse(content);
        if (Array.isArray(data) && data.every(item => 
          item.id && item.timestamp && item.message)) {
          resolve(data as DebugRecord[]);
        } else {
          reject(new Error('文件格式不正确'));
        }
      } catch {
        reject(new Error('无法解析JSON文件'));
      }
    };
    reader.onerror = () => reject(new Error('读取文件失败'));
    reader.readAsText(file);
  });
};

export const formatTimestamp = (timestamp: number): string => {
  const date = new Date(timestamp);
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false
  });
};

export const generateUniqueId = (): string => {
  return Date.now().toString(36) + Math.random().toString(36).substring(2);
}; 