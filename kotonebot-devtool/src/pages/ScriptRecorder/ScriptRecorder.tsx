import React, { useState, useEffect, useRef, useCallback } from 'react';
import styled from '@emotion/styled';
import VSToolBar from '../../components/VSToolBar';
import ImageEditor, { AnnotationChangedEvent } from '../../components/ImageEditor/ImageEditor';
import { MdDevices, MdPlayArrow, MdSearch, MdTouchApp, MdTextFields, MdTextSnippet, MdCropFree, MdRefresh, MdPause, MdBackHand, MdCheck, MdClose, MdEdit, MdContentCopy, MdContentCut, MdFolder } from 'react-icons/md';
import AceEditor from 'react-ace';
import { Splitable } from '../../components/Splitable';
import { Tool, Annotation } from '../../components/ImageEditor/types';
import { create } from 'zustand';

// 引入 ace 编辑器的主题和语言模式
import 'ace-builds/src-noconflict/mode-python';
import 'ace-builds/src-noconflict/theme-monokai';
import 'ace-builds/src-noconflict/theme-chrome';
import 'ace-builds/src-noconflict/ext-language_tools';
import { css } from '@emotion/react';
import useImageMetaData, { Definition, DefinitionType, ImageMetaData, TemplateDefinition } from '../../hooks/useImageMetaData';
import { useDarkMode } from '../../hooks/useDarkMode';
import { useDebugClient } from '../../store/debugStore';
import useLatestCallback from '../../hooks/useLatestCallback';
import useHotkey from '../../hooks/useHotkey';
import { useFormModal } from '../../hooks/useFormModal';
import { openDirectory } from '../../utils/fileUtils';

const Container = styled.div`
  display: flex;
  flex-direction: column;
  height: 100vh;
`;

const ImageViewerWrapper = styled.div`
  height: 100%;
`;

const CodeEditorWrapper = styled.div`
  height: 100%;
  background-color: #1e1e1e;
  display: flex;
  flex-direction: column;
`;

type ScriptRecorderTool = 'drag' | 'template' | 'template-click' | 'ocr' | 'ocr-click' | 'hint-box';

interface ScriptRecorderState {
    code: string;
    tool: ScriptRecorderTool;
    autoScreenshot: boolean;
    connected: boolean;
    imageUrl: string;
    inEditMode: boolean;
    directoryHandle: FileSystemDirectoryHandle | null;

    imageMetaDataObject: ReturnType<typeof useImageMetaData> | null;
    setImageMetaDataObject: (imageMetaData: ReturnType<typeof useImageMetaData>) => void;

    setCode: (code: string) => void;
    setTool: (tool: ScriptRecorderTool) => void;
    setAutoScreenshot: (auto: boolean) => void;
    setConnected: (connected: boolean) => void;
    setImageUrl: (url: string) => void;

    setDirectoryHandle: (handle: FileSystemDirectoryHandle | null) => void;
    enterEditMode: () => void;
    exitEditMode: () => void;
}


const useScriptRecorderStore = create<ScriptRecorderState>((set) => ({
    code: '',
    tool: 'drag',
    autoScreenshot: true,
    connected: false,
    imageUrl: '',
    inEditMode: false,
    directoryHandle: null,

    imageMetaDataObject: null,
    setImageMetaDataObject: (imageMetaData) => set({ imageMetaDataObject: imageMetaData }),

    setCode: (code) => set({ code }),
    setTool: (tool) => set({ tool }),
    setAutoScreenshot: (auto) => set({ autoScreenshot: auto }),
    setConnected: (connected) => set({ connected }),
    setImageUrl: (url) => set({ imageUrl: url }),
    setDirectoryHandle: (handle) => set({ directoryHandle: handle }),
    enterEditMode: () => set({ inEditMode: true, autoScreenshot: false }),
    exitEditMode: () => set({ inEditMode: false }),
}));


interface ToolConfigItem {
    code?: (d: Definition, a: Annotation) => string;
}

const ToolConfig: Record<ScriptRecorderTool, ToolConfigItem> = {
    'drag': {
    },
    'template': {
        code: (d: Definition) => `image.find(R.${d.name})`,

    },
    'template-click': {
        code: (d: Definition) => 
            `if image.find(R.${d.name}):\n\tdevice.click()`,
    },
    'ocr': {
        code: (d: Definition) => `ocr.ocr(R.${d.name})`,
    },
    'ocr-click': {
        code: (d: Definition) => 
            `if ocr.ocr(R.${d.name}):\n\tdevice.click()`,
    },
    'hint-box': {
    },
}



interface ViewToolBarProps {
    onOpenDirectory: () => void;
}

const ViewToolBar: React.FC<ViewToolBarProps> = ({
    onOpenDirectory,
}) => {
    const { connected, autoScreenshot, setAutoScreenshot, directoryHandle, enterEditMode, setImageUrl } = useScriptRecorderStore();
    const client = useDebugClient();

    const handleCapture = async () => {
        const url = await client.screenshot();
        setImageUrl(url);
    };

    return (
        <VSToolBar align='center'>
            <VSToolBar.Button
                id="open-directory"
                icon={<MdFolder />}
                label="打开文件夹"
                onClick={onOpenDirectory}
            />
            <VSToolBar.Button
                id="device-status"
                icon={<MdDevices style={{ color: connected ? undefined : '#ff4444' }} />}
                label={<span style={{ color: connected ? undefined : '#ff4444' }}>{connected ? "设备已连接" : "设备未连接"}</span>}
                onClick={() => { }}
            />
            <VSToolBar.Button
                icon={autoScreenshot ? <MdPause /> : <MdPlayArrow />}
                id="auto-update"
                label={autoScreenshot ? "自动截图 ON" : "自动截图 OFF"}
                onClick={() => setAutoScreenshot(!autoScreenshot)}
            />
            {!autoScreenshot && (
                <VSToolBar.Button
                    icon={<MdRefresh />}
                    id="manual-capture"
                    label="立即截图"
                    onClick={handleCapture}
                />
            )}
            <VSToolBar.Separator />
            <VSToolBar.Button
                id="enter-edit"
                icon={<MdEdit />}
                label="进入编辑"
                onClick={enterEditMode}
                disabled={!directoryHandle}
            />
        </VSToolBar>
    );
};

interface EditToolBarProps {
    onClear: () => void;
}

const EditToolBar: React.FC<EditToolBarProps> = ({
    onClear,
}) => {
    const { tool, setTool, exitEditMode, imageUrl, directoryHandle, imageMetaDataObject } = useScriptRecorderStore();
    const { modal, show: showFormModal } = useFormModal([
        {
            type: 'text',
            label: '名称',
            name: 'name',
            required: true,
            placeholder: '请输入文件名'
        }
    ]);
    
    const handleToolChange = (newTool: ScriptRecorderTool) => {
        if (newTool === tool)
            setTool('drag');
        else
            setTool(newTool);
    };

    const handleConfirm = async () => {
        if (!directoryHandle) return;

        const result = await showFormModal('保存文件');
        if (!result) return;

        const name = result.name;
        
        try {
            // 保存图片
            const imageResponse = await fetch(imageUrl);
            const imageBlob = await imageResponse.blob();
            const imageFile = await directoryHandle.getFileHandle(`${name}.png`, { create: true });
            const imageWritable = await imageFile.createWritable();
            await imageWritable.write(imageBlob);
            await imageWritable.close();

            // 保存元数据
            const metaFile = await directoryHandle.getFileHandle(`${name}.png.json`, { create: true });
            const metaWritable = await metaFile.createWritable();
            await metaWritable.write(JSON.stringify(imageMetaDataObject?.imageMetaData, null, 2));
            await metaWritable.close();

            // 清理并退出
            imageMetaDataObject?.clear();
            exitEditMode();
        } catch (error) {
            console.error('保存文件失败:', error);
        }
    };

    return (
        <VSToolBar align='center'>
            {modal}
            <VSToolBar.Button
                id="drag"
                icon={<MdBackHand />}
                label="拖动 (V)"
                selected={tool === 'drag'}
                onClick={() => handleToolChange('drag')}
            />
            <VSToolBar.Button
                id="templ-find"
                icon={<MdSearch />}
                label="找图 (T)"
                selected={tool === 'template'}
                onClick={() => handleToolChange('template')}
            />
            <VSToolBar.Button
                id="templ-click"
                icon={<MdTouchApp />}
                label="找图并点击 (R)"
                selected={tool === 'template-click'}
                onClick={() => handleToolChange('template-click')}
            />
            <VSToolBar.Button
                id="ocr-find"
                icon={<MdTextFields />}
                label="OCR (S)"
                selected={tool === 'ocr'}
                onClick={() => handleToolChange('ocr')}
            />
            <VSToolBar.Button
                id="ocr-click"
                icon={<MdTextSnippet />}
                label="OCR 并点击 (A)"
                selected={tool === 'ocr-click'}
                onClick={() => handleToolChange('ocr-click')}
            />
            <VSToolBar.Button
                id="hint-box"
                icon={<MdCropFree />}
                label="HintBox (B)"
                selected={tool === 'hint-box'}
                onClick={() => handleToolChange('hint-box')}
            />
            <VSToolBar.Separator />
            <VSToolBar.Button
                id="confirm"
                icon={<MdCheck />}
                label="完成"
                onClick={handleConfirm}
            />
            <VSToolBar.Button
                id="cancel"
                icon={<MdClose />}
                label="取消"
                onClick={() => {
                    onClear();
                    setTool('drag');
                    exitEditMode();
                }}
            />
        </VSToolBar>
    );
};

interface CodeEditorToolBarProps {
    onCopyAll: () => void;
    onCutAll: () => void;
}

const CodeEditorToolBar: React.FC<CodeEditorToolBarProps> = ({
    onCopyAll,
    onCutAll,
}) => {
    return (
        <VSToolBar align='center'>
            <VSToolBar.Button
                id="run"
                icon={<MdPlayArrow />}
                label="运行"
                disabled={true}
            />
            <VSToolBar.Separator />
            <VSToolBar.Button
                id="copy-all"
                icon={<MdContentCopy />}
                label="复制全部"
                onClick={onCopyAll}
            />
            <VSToolBar.Button
                id="cut-all"
                icon={<MdContentCut />}
                label="剪切全部"
                onClick={onCutAll}
            />
        </VSToolBar>
    );
};

function useStoreImageMetaData() {
    const setImageMetaDataObject = useScriptRecorderStore((state) => state.setImageMetaDataObject);
    const ret = useImageMetaData();
    setImageMetaDataObject(ret);
    return ret;
}

const ScriptRecorder: React.FC = () => {
    const client = useDebugClient();
    const editorRef = useRef<any>(null);
    const { imageMetaData, Definitions, Annotations, clear } = useStoreImageMetaData();
    const code = useScriptRecorderStore((s) => s.code);
    const tool = useScriptRecorderStore((s) => s.tool);
    const autoScreenshot = useScriptRecorderStore((s) => s.autoScreenshot);
    const imageUrl = useScriptRecorderStore((s) => s.imageUrl);
    const inEditMode = useScriptRecorderStore((s) => s.inEditMode);
    const setCode = useScriptRecorderStore((s) => s.setCode);
    const setTool = useScriptRecorderStore((s) => s.setTool);
    const setConnected = useScriptRecorderStore((s) => s.setConnected);
    const setImageUrl = useScriptRecorderStore((s) => s.setImageUrl);
    const setDirectoryHandle = useScriptRecorderStore((s) => s.setDirectoryHandle);



    const { theme: editorTheme } = useDarkMode({
        whenDark: 'monokai',
        whenLight: 'chrome'
    });

    const { modal: formModal, show: showFormModal } = useFormModal([
        {
            type: 'text',
            label: '名称',
            name: 'name',
            required: true,
            placeholder: '请输入名称'
        },
        {
            type: 'text',
            label: '显示名称',
            name: 'displayName',
            required: true,
            placeholder: '请输入显示名称'
        }
    ]);

    const updateScreenshot = useLatestCallback(async () => {
        window.setTimeout(async () => {
            if (!autoScreenshot)
                return;
            const url = await client.screenshot();
            if (!autoScreenshot)
                return;
            setImageUrl(url);
            if (!autoScreenshot)
                return;
            window.setTimeout(updateScreenshot, 10);
        }, 10);
    });

    useEffect(() => {
        if (autoScreenshot)
            updateScreenshot();
    }, [autoScreenshot, updateScreenshot]);

    useEffect(() => {
        client.addEventListener('connectionStatus', (e) => {
            if (e.connected) {
                setImageUrl(`http://${client.host}/api/screenshot?t=${Date.now()}`);
            }
            setConnected(e.connected);
        });
    }, [client]);
    
    const handleAnnotationChange = async (e: AnnotationChangedEvent) => {
        if (e.type === 'add') {

            let type: DefinitionType | undefined;
            if (tool === 'template' || tool === 'template-click')
                type = 'template';
            else if (tool === 'ocr' || tool === 'ocr-click')
                type = 'ocr';
            else if (tool === 'hint-box')
                type = 'hint-box';
            if (!type) {
                return;
            }

            Annotations.add(e.annotation);
            const definition = {
                name: '',
                displayName: '',
                type: type,
                annotationId: e.annotation.id,
                useHintRect: false,
            } as TemplateDefinition;
            Definitions.add(definition);

            const formResult = await showFormModal('编辑标注');
            if (formResult) {
                Definitions.update({
                    ...definition,
                    name: formResult.name,
                    displayName: formResult.displayName
                });
                Annotations.update({
                    id: e.annotation.id,
                    _tip: formResult.displayName
                });

                // 根据工具类型插入相应的代码
                if (tool in ToolConfig) {
                    const codeTemplate = ToolConfig[tool as keyof typeof ToolConfig].code?.(
                        { ...definition, name: formResult.name },
                        e.annotation
                    );
                    
                    const editor = editorRef.current?.editor;
                    if (editor && codeTemplate) {
                        const session = editor.getSession();
                        const position = editor.getCursorPosition();
                        const currentLine = session.getLine(position.row);
                        
                        // 如果当前行不为空且不是以换行符结尾，先添加换行符
                        const insertText = (currentLine && currentLine.trim() !== '' ? '\n' : '') + codeTemplate;
                        
                        editor.insert(insertText);
                    }
                }
            } else {
                Annotations.remove(e.annotation.id);
                Definitions.remove(e.annotation.id);
            }
            setTool('drag');
        } else if (e.type === 'update') {
            Annotations.update(e.annotation);
        } else if (e.type === 'remove') {
            Annotations.remove(e.annotation.id);
            Definitions.remove(e.annotation.id);
        }
    };

    // 热键支持
    useHotkey([
        {
            key: 'v',
            single: true,
            callback: () => setTool('drag')
        },
        {
            key: 't',
            single: true,
            callback: () => setTool('template')
        },
        {
            key: 'r',
            single: true,
            callback: () => setTool('template-click')
        },
        {
            key: 's',
            single: true,
            callback: () => setTool('ocr')
        },
        {
            key: 'a',
            single: true,
            callback: () => setTool('ocr-click')
        },
        {
            key: 'b',
            single: true,
            callback: () => setTool('hint-box')
        }
    ]);

    const handleCopyAll = () => {
        const editor = editorRef.current?.editor;
        if (editor) {
            const text = editor.getValue();
            navigator.clipboard.writeText(text);
        }
    };

    const handleCutAll = () => {
        const editor = editorRef.current?.editor;
        if (editor) {
            const text = editor.getValue();
            navigator.clipboard.writeText(text);
            editor.setValue('');
        }
    };

    const handleOpenDirectory = async () => {
        const handle = await openDirectory();
        setDirectoryHandle(handle);
    };

    return (
        <Container>
            {formModal}
            {inEditMode ? (
                <EditToolBar
                    onClear={clear}
                />
            ) : (
                <ViewToolBar
                    onOpenDirectory={handleOpenDirectory}
                />
            )}
            <div css={css`height: 100%; margin-top: 0;`}>
                <Splitable>
                    <ImageViewerWrapper>
                        <ImageEditor
                            enableMask
                            image={imageUrl}
                            tool={tool === 'drag' ? Tool.Drag : Tool.Rect}
                            annotations={imageMetaData.annotations}
                            onAnnotationChanged={handleAnnotationChange}
                        />
                    </ImageViewerWrapper>
                    <CodeEditorWrapper>
                        <CodeEditorToolBar
                            onCopyAll={handleCopyAll}
                            onCutAll={handleCutAll}
                        />
                        <AceEditor
                            ref={editorRef}
                            mode="python"
                            theme={editorTheme}
                            value={code}
                            onChange={setCode}
                            name="script-editor"
                            width="100%"
                            height="100%"
                            fontSize={14}
                            showPrintMargin={false}
                            showGutter={true}
                            highlightActiveLine={true}
                            setOptions={{
                                enableBasicAutocompletion: true,
                                enableLiveAutocompletion: true,
                                enableSnippets: true,
                                showLineNumbers: true,
                                tabSize: 4,
                            }}
                        />
                    </CodeEditorWrapper>
                </Splitable>
            </div>
        </Container>
    );
};

export default ScriptRecorder;
