export interface FileResult {
    file: File;
    name: string;
    handle?: FileSystemFileHandle;
    fileSystem: 'wfs' | 'input';
}

export interface OpenFilesOptions {
    accept?: string;
    multiple?: boolean;
}

export interface OpenFilesResult {
    files: FileResult[];
}

/**
 * 使用传统的 input 标签上传文件
 */
export const openFileInput = async (options: OpenFilesOptions = {}): Promise<OpenFilesResult> => {
    const { 
        multiple = false,
    } = options;

    return new Promise((resolve) => {
        const input = document.createElement('input');
        input.type = 'file';
        input.accept = '.json,.png,.jpg,.jpeg';
        input.multiple = multiple;
        
        input.onchange = async (e) => {
            const files = Array.from((e.target as HTMLInputElement).files || []);
            if (files.length === 0) {
                resolve({ files: [] });
                return;
            }

            const results: FileResult[] = [];
            
            for (const file of files) {
                const result: FileResult = {
                    file,
                    name: file.name,
                    fileSystem: 'input'
                };

                try {
                    results.push(result);
                } catch (error) {
                    console.error(`Failed to read file ${file.name}:`, error);
                    throw new Error(`无法读取文件 ${file.name}`);
                }
            }

            resolve({ files: results });
        };

        input.click();
    });
};

/**
 * 使用 Web File System API 打开文件
 */
export const openFileWFS = async (options: OpenFilesOptions = {}): Promise<OpenFilesResult> => {
    const { 
        multiple = false,
    } = options;

    try {
        // @ts-ignore - FileSystemHandle API 可能在某些环境下不支持
        const handles = await window.showOpenFilePicker({
            types: [
                {
                    description: '图片文件 / meta 数据',
                    accept: {
                        'image/jpeg': ['.jpg', '.jpeg'],
                        'image/png': ['.png'],
                        'application/json': ['.json']
                    }
                },
            ],
            multiple
        });

        const results: FileResult[] = [];
        
        for (const handle of handles) {
            const file = await handle.getFile();
            results.push({
                file,
                name: file.name,
                handle,
                fileSystem: 'wfs'
            });
        }

        return { files: results };
    } catch (error) {
        if ((error as Error).name === 'AbortError') {
            return { files: [] };
        }
        throw error;
    }
};

/**
 * 打开文件。优先使用 FileSystem API，失败时回退到上传方式
 */
export const openFiles = async (options: OpenFilesOptions = {}): Promise<OpenFilesResult> => {
    try {
        // @ts-ignore - 检查是否支持 FileSystem API
        if (window.showOpenFilePicker) {
            return await openFileWFS(options);
        } else {
            return await openFileInput(options);
        }
    } catch (error) {
        return await openFileInput(options);
    }
};

/**
 * 将文件读取为文本
 */
export const readFileAsText = (file: File): Promise<string> => {
    return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = (e) => resolve(e.target?.result as string);
        reader.onerror = reject;
        reader.readAsText(file);
    });
};

/**
 * 将文件读取为DataURL
 */
export const readFileAsDataURL = (file: File): Promise<string> => {
    return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = (e) => resolve(e.target?.result as string);
        reader.onerror = reject;
        reader.readAsDataURL(file);
    });
};

/**
 * 将文件读取为JSON对象
 */
export const readFileAsJSON = (file: File): Promise<any> => {
    return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = (e) => {
            try {
                const json = JSON.parse(e.target?.result as string);
                resolve(json);
            } catch (error) {
                reject(error);
            }
        };
        reader.onerror = reject;
        reader.readAsText(file);
    });
};


/**
 * 保存JSON数据到文件
 */
export const downloadJSONToFile = (data: any, filename: string) => {
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
};

/**
 * 裁剪图片
 */
export const cropImage = (
    img: HTMLImageElement, 
    rect: { x1: number, y1: number, x2: number, y2: number }
): string => {
    const canvas = document.createElement('canvas');
    const ctx = canvas.getContext('2d');
    const width = rect.x2 - rect.x1;
    const height = rect.y2 - rect.y1;
    canvas.width = width;
    canvas.height = height;

    ctx?.drawImage(
        img,
        rect.x1, rect.y1, width, height,
        0, 0, width, height
    );

    return canvas.toDataURL('image/png');
};

/**
 * 使用 Web File System API 创建新文件并保存
 * @param content 要保存的内容（字符串、Blob 或 ArrayBuffer）
 * @param suggestedName 建议的文件名
 * @returns 新的 FileSystemFileHandle 对象
 */
export const saveFileAsWFS = async (content: string | Blob | ArrayBuffer, suggestedName: string): Promise<FileSystemFileHandle> => {
    try {
        // @ts-ignore - FileSystemHandle API 可能在某些环境下不支持
        const handle = await window.showSaveFilePicker({
            suggestedName,
            types: [
                {
                    description: 'JSON 文件',
                    accept: {
                        'application/json': ['.json']
                    }
                }
            ]
        });
        
        // 获取写入权限并写入内容
        const writable = await handle.createWritable();
        await writable.write(content);
        await writable.close();
        
        return handle;
    } catch (error) {
        console.error('Failed to save file:', error);
        throw new Error('保存文件失败');
    }
};

/**
 * 使用 Web File System API 保存文件
 * @param handle FileSystemFileHandle 对象，如果为空则会弹出另存为对话框
 * @param content 要保存的内容（字符串、Blob 或 ArrayBuffer）
 * @param suggestedName 当需要另存为时的建议文件名
 * @returns 如果是另存为，则返回新的 FileSystemFileHandle；否则返回原来的 handle
 */
export const saveFileWFS = async (
    handle: FileSystemFileHandle | undefined | null,
    content: string | Blob | ArrayBuffer,
    suggestedName?: string
): Promise<FileSystemFileHandle> => {
    try {
        if (!handle) {
            // 如果没有 handle，执行另存为操作
            return await saveFileAsWFS(content, suggestedName || 'metadata.json');
        }

        // 有 handle，直接保存
        const writable = await handle.createWritable();
        await writable.write(content);
        await writable.close();
        return handle;
    } catch (error) {
        console.error('Failed to save file:', error);
        throw new Error('保存文件失败');
    }
};

/**
 * 检查文件是否是通过 Web File System API 打开的
 * @param fileResult FileResult 对象
 * @returns 是否可以使用 WFS API 保存
 */
export const canSaveWithWFS = (fileResult?: FileResult): boolean => {
    return !!fileResult?.handle;
};

/**
 * 使用 Web File System API 保存图片数据到文件
 * @param handle FileSystemFileHandle 对象
 * @param imageData 图片数据（Base64 或 Blob）
 */
export const saveImageWithHandle = async (handle: FileSystemFileHandle, imageData: string | Blob): Promise<void> => {
    if (typeof imageData === 'string' && imageData.startsWith('data:')) {
        // 将 Base64 转换为 Blob
        const response = await fetch(imageData);
        imageData = await response.blob();
    }
    await saveFileWFS(handle, imageData);
};
