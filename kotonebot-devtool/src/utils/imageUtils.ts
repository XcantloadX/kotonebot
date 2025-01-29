import { ViewState } from '../types/debug';

export const DEFAULT_VIEW_STATE: ViewState = {
  scale: 1,
  x: 0,
  y: 0,
  locked: false,
};

export const calculateImageDimensions = (
  imageWidth: number,
  imageHeight: number,
  containerWidth: number,
  containerHeight: number
): { width: number; height: number; scale: number } => {
  const imageRatio = imageWidth / imageHeight;
  const containerRatio = containerWidth / containerHeight;

  let scale = 1;
  let width = imageWidth;
  let height = imageHeight;

  if (imageRatio > containerRatio) {
    // 图片更宽，以容器宽度为基准
    if (imageWidth > containerWidth) {
      scale = containerWidth / imageWidth;
      width = containerWidth;
      height = imageHeight * scale;
    }
  } else {
    // 图片更高，以容器高度为基准
    if (imageHeight > containerHeight) {
      scale = containerHeight / imageHeight;
      height = containerHeight;
      width = imageWidth * scale;
    }
  }

  return { width, height, scale };
};

export const calculateZoom = (
  currentScale: number,
  delta: number,
  minScale = 0.1,
  maxScale = 5
): number => {
  const ZOOM_SENSITIVITY = 0.001;
  const newScale = currentScale * (1 - delta * ZOOM_SENSITIVITY);
  return Math.min(Math.max(newScale, minScale), maxScale);
};

export const getImageUrl = (
  type: 'memory' | 'file',
  path: string,
  baseUrl = ''
): string => {
  if (type === 'memory') {
    return `${baseUrl}/api/read_memory?key=${encodeURIComponent(path)}`;
  }
  return `${baseUrl}/api/read_file?path=${encodeURIComponent(path)}`;
};

export const downloadImage = async (url: string, filename: string): Promise<void> => {
  try {
    const response = await fetch(url);
    const blob = await response.blob();
    const objectUrl = URL.createObjectURL(blob);
    
    const link = document.createElement('a');
    link.href = objectUrl;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    
    URL.revokeObjectURL(objectUrl);
  } catch (error) {
    console.error('下载图片失败:', error);
    throw error;
  }
}; 