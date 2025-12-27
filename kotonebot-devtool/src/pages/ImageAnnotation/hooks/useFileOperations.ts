import { useCallback } from 'react';
import { useMessageBox } from '../../../hooks/useMessageBox';
import { useToast } from '../../../components/ToastMessage';
import { openFileWFS, readFileAsDataURL, readFileAsJSON, saveFileAsWFS, saveFileWFS, FileResult } from '../../../utils/fileUtils';
import { ImageMetaData } from '../types/definitions';
import { useImmer } from 'use-immer';

export interface FileOperations {
    open: () => Promise<void>;
    save: () => Promise<void>;
    drop: (result: FileResult) => Promise<void>;
    currentFile: FileResult | null;
}

export interface UseFileOperationsProps {
    isDirty: boolean;
    imageMetaData: ImageMetaData;
    toString: (data: ImageMetaData) => string;
    onLoad: (metaData: ImageMetaData, imageUrl?: string, fileName?: string, fileResult?: FileResult) => void;
    onClear: () => void;
    onSetImageUrl: (url: string, fileName: string) => void;
}

export function useFileOperations({
    isDirty,
    imageMetaData,
    toString,
    onLoad,
    onClear,
    onSetImageUrl,
}: UseFileOperationsProps): FileOperations {
    const { yesNo } = useMessageBox();
    const { showToast } = useToast();
    const [currentFile, setCurrentFile] = useImmer<FileResult | null>(null);

    const open = useCallback(async () => {
        if (isDirty) {
            const result = await yesNo({ title: '未保存的修改', text: '当前有未保存的修改，是否继续？' });
            if (result === 'no') return;
        }

        try {
            const result = await openFileWFS({ accept: 'image/*,.json', multiple: true });
            const imageFile = result.files.find(f => f.file.type.startsWith('image/'));
            const jsonFile = result.files.find(f => f.file.name.endsWith('.json'));

            let metaData: ImageMetaData | null = null;
            if (jsonFile) {
                metaData = await readFileAsJSON(jsonFile.file) as ImageMetaData;
                setCurrentFile(jsonFile);
            } else {
                onClear();
                setCurrentFile(null);
            }

            if (imageFile) {
                const imageUrl = await readFileAsDataURL(imageFile.file);
                if (metaData) {
                    onLoad(metaData, imageUrl, imageFile.name, jsonFile);
                } else {
                    onSetImageUrl(imageUrl, imageFile.name);
                }
            } else if (metaData) {
                onLoad(metaData, undefined, undefined, jsonFile);
            }

            showToast('success', '加载成功', '加载成功');
        } catch (error) {
            showToast('danger', '加载失败', error instanceof Error ? error.message : '无法加载文件');
        }
    }, [isDirty, yesNo, showToast, onLoad, onClear, onSetImageUrl, setCurrentFile]);

    const save = useCallback(async () => {
        const fileName = currentFile?.name || 'metadata.json';
        const content = toString(imageMetaData);

        try {
            const handle = currentFile?.fileSystem === 'wfs'
                ? await saveFileWFS(currentFile.handle, content, fileName)
                : await saveFileAsWFS(content, fileName);
            
            const file = await handle.getFile();
            setCurrentFile({ file, name: file.name, handle, fileSystem: 'wfs' });
            showToast('success', '保存成功', '保存成功');
        } catch (error) {
            showToast('danger', '保存失败', '无法保存文件');
        }
    }, [currentFile, imageMetaData, toString, showToast, setCurrentFile]);

    const drop = useCallback(async (result: FileResult) => {
        const imageUrl = await readFileAsDataURL(result.file);
        onClear();
        setCurrentFile(null);
        onSetImageUrl(imageUrl, result.name);
    }, [onClear, onSetImageUrl, setCurrentFile]);

    return { open, save, drop, currentFile };
}
