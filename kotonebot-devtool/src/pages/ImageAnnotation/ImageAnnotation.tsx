import React, { useCallback, useEffect, useRef, useState } from 'react';
import styled from '@emotion/styled';
import { SideToolBar, Tool } from '../../components/SideToolBar';
import PropertyGrid, { Property, PropertyCategory } from '../../components/PropertyGrid';
import ImageEditor, { AnnotationChangedEvent } from '../../components/ImageEditor/ImageEditor';
import { Annotation, Tool as EditorTool } from '../../components/ImageEditor/types';
import { BsCursor, BsSquare, BsFolder2Open, BsFloppy, BsCardImage, BsQuestionSquare } from 'react-icons/bs';
import useImageMetaData, { Definition, DefinitionType, ImageMetaData, TemplateDefinition, Definitions } from '../../hooks/useImageMetaData';
import { useImageViewerModal } from '../../components/ImageViewerModal';
import { useMessageBox } from '../../hooks/useMessageBox';
import { useToast } from '../../components/ToastMessage';
import DragArea from './DragArea';
import { cropImage, openFileWFS, openFileInput, downloadJSONToFile, readFileAsJSON, readFileAsDataURL, FileResult, saveFileWFS, saveFileAsWFS } from '../../utils/fileUtils';
import NativeDiv from '../../components/NativeDiv';
import useHotkey from '../../hooks/useHotkey';

const PageContainer = styled.div`
  display: flex;
  width: 100%;
  height: 100vh;
  gap: 16px;
  padding: 16px;
  background-color: #f8f9fa;
`;

const EditorContainer = styled(NativeDiv)`
  flex: 1;
  min-width: 0;
  background-color: white;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
`;

const PropertyContainer = styled.div`
  width: 300px;
  background-color: white;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  padding: 16px;
`;

const Tip = styled.span`
  font-weight: bold;
  color: white;
  text-shadow: 
    -1px -1px 0 black,
    1px -1px 0 black,
    -1px 1px 0 black,
    1px 1px 0 black;
`;

// 工具栏配置
export enum Tools {
    Drag = EditorTool.Drag,
    Template = 'template',
    HintBox = 'hintbox',
}

const tools: Array<Tool | 'separator'> = [
    {
        id: 'open',
        icon: <BsFolder2Open size={24} />,
        title: '打开',
        selectable: false,
    },
    {
        id: 'save',
        icon: <BsFloppy size={24} />,
        title: '保存',
        selectable: false,
    },
    'separator',
    {
        id: Tools.Drag,
        icon: <BsCursor size={24} />,
        title: '拖动工具 (V)',
        selectable: true,
    },
    {
        id: Tools.Template,
        icon: <BsCardImage size={24} />,
        title: '模板工具 (T)', 
        selectable: true,
    },
    {
        id: Tools.HintBox,
        icon: <BsQuestionSquare size={24} />,
        title: 'HintBox 工具 (B)',
        selectable: true,
    }
];
const STR_TO_TOOL: Record<string, Tools> = {
    drag: Tools.Drag,
    template: Tools.Template,
    hintbox: Tools.HintBox,
};

const TOOL_TO_EDITOR_TOOL: Record<Tools, EditorTool> = {
    [Tools.Drag]: EditorTool.Drag,
    [Tools.Template]: EditorTool.Rect,
    [Tools.HintBox]: EditorTool.Rect,
};

// 计算最大公约数
const gcd = (a: number, b: number): number => {
    a = Math.abs(a);
    b = Math.abs(b);
    while (b) {
        const t = b;
        b = a % b;
        a = t;
    }
    return a;
};

// 计算最简比例
const getSimplestRatio = (width: number, height: number): string => {
    const divisor = gcd(width, height);
    const simpleWidth = width / divisor;
    const simpleHeight = height / divisor;
    return `${simpleWidth}:${simpleHeight}`;
};

// 属性栏数据 Hook
const usePropertyGridData = (
    selectedAnnotation: Annotation | null,
    definitions: Definitions,
    image: HTMLImageElement | null,
    onImageClick: (imageUrl: string) => void,
    onDefinitionChange?: (id: string, changes: Partial<TemplateDefinition>) => void,
    imageFileName?: string,
    annotations?: Annotation[],
    currentFileResult?: FileResult | null
) => {
    const [croppedImageUrl, setCroppedImageUrl] = React.useState<string>('');

    React.useEffect(() => {
        if (selectedAnnotation && image) {
            const url = cropImage(image, selectedAnnotation.data);
            setCroppedImageUrl(url);
        } else {
            setCroppedImageUrl('');
        }
    }, [selectedAnnotation, image]);

    if (!selectedAnnotation) {
        if (!image) return [];

        return [
            {
                title: '文件名',
                render: () => imageFileName || '未命名',
            },
            {
                title: '打开方式',
                render: () => currentFileResult?.fileSystem === 'wfs' ? 'WebFileSystem' : 'Input',
            },
            {
                title: '宽高',
                render: () => `${image.width} × ${image.height}`,
            },
            {
                title: '宽高比',
                render: () => getSimplestRatio(image.width, image.height),
            },
            {
                title: '标注数量',
                render: () => annotations?.length || 0,
            }
        ];
    }

    const definition = definitions[selectedAnnotation.id];
    if (!definition) {
        return [];
    }
    const { x1, y1, x2, y2 } = selectedAnnotation.data;


    const generalProperties: Array<PropertyCategory | Property> = [
        {
            render: () => {
                if (!image) return <span>图片加载中...</span>;
                if (!croppedImageUrl) return <span>裁剪中...</span>;
                return (
                    <div style={{
                        height: '100px',
                        margin: '0 auto'
                    }}>
                        <img
                            src={croppedImageUrl}
                            style={{
                                maxWidth: '100%',
                                maxHeight: '100px',
                                objectFit: 'contain',
                                cursor: 'pointer',
                            }}
                            onClick={() => onImageClick(croppedImageUrl)}
                        />
                    </div>
                );
            },
        },
        {
            title: '通用',
            properties: [
                {
                    title: '名称',
                    render: {
                        type: 'text',
                        required: true,
                        value: definition.name,
                        onChange: (value: string) => onDefinitionChange?.(selectedAnnotation.id, { name: value }),
                    }
                },
                {
                    title: '显示名称',
                    render: {
                        type: 'text',
                        required: true,
                        value: definition.displayName,
                        onChange: (value: string) => onDefinitionChange?.(selectedAnnotation.id, { displayName: value }),
                    }
                },
                {
                    title: '类型',
                    render: () => definition.type,
                }
            ],
            foldable: true
        },
    ];
    const annotationProperties: Array<PropertyCategory | Property> = [
        {
            title: '标注',
            properties: [
                {
                    title: 'ID',
                    render: () => selectedAnnotation.id,
                },
                {
                    title: '类型',
                    render: () => '矩形',
                },
                {
                    title: '范围',
                    render: () => `(${x1}, ${y1}, ${x2}, ${y2})`,
                },
                {
                    title: '宽高',
                    render: () => `${x2 - x1} × ${y2 - y1}`,
                }
            ],
            foldable: true
        }
    ];

    let specificProperties: Array<PropertyCategory | Property> = [];
    if (definition.type === 'template') {
        const rectDef = definition as TemplateDefinition;
        specificProperties = [
            {
                title: '模板',
                properties: [
                    {
                        title: '提示矩形',
                        render: {
                            type: 'checkbox',
                            required: false,
                            value: rectDef.useHintRect,
                            onChange: (value: boolean) => onDefinitionChange?.(selectedAnnotation.id, { useHintRect: value }),
                        }
                    }
                ],
                foldable: true,
            }
        ];
    }

    return [
        ...generalProperties,
        ...specificProperties,
        ...annotationProperties,
    ];
};

const ImageAnnotation: React.FC = () => {
    const [currentTool, setCurrentTool] = useState<Tools>(Tools.Drag);

    const { imageMetaData, Definitions, Annotations, clear, load, toString, fromString } = useImageMetaData();
    const [selectedAnnotation, setSelectedAnnotation] = useState<Annotation | null>(null);
    const [isDirty, setIsDirty] = useState(false);
    const [image, setImage] = useState<HTMLImageElement | null>(null);
    const imageFileNameRef = useRef<string>('');
    const { modal, openModal } = useImageViewerModal('裁剪预览');
    const [imageUrl, setImageUrl] = useState<string>('');
    const { yesNo, MessageBoxComponent } = useMessageBox();
    const { showToast, ToastComponent } = useToast();
    const currentFileResult = useRef<FileResult | null>(null);

    // 预加载图片
    useEffect(() => {
        const img = new Image();
        img.crossOrigin = 'anonymous';
        img.onload = () => {
            setImage(img);
        };
        img.src = imageUrl;
    }, [imageUrl]);

    const loadImage = useCallback((imageUrl: string, shouldClearMetaData: boolean = true) => {
        setImageUrl(imageUrl);
        if (shouldClearMetaData) {
            // 只有在不是同时加载 meta 数据时才清空标注
            clear();
            setSelectedAnnotation(null);
            setIsDirty(false);
        }
    }, [clear]);

    const handleImageLoad = useCallback(async (result: FileResult, shouldClearMetaData: boolean = true) => {
        currentFileResult.current = result;
        imageFileNameRef.current = result.name;
        const dataUrl = await readFileAsDataURL(result.file);
        loadImage(dataUrl, shouldClearMetaData);
    }, [loadImage]);


    const handleAnnotationChange = (e: AnnotationChangedEvent) => {
        if (e.type === 'add') {
            let type: DefinitionType | undefined = undefined;
            if (currentTool === Tools.Template) {
                type = 'template';
            }
            else if (currentTool === Tools.HintBox) {
                type = 'hint-box';
            }
            if (!type) {
                showToast('danger', '错误', '无法识别的标注类型');
                return;
            }
            Annotations.add(e.annotation);
            Definitions.add({
                name: '',
                displayName: '',
                type: type,
                annotationId: e.annotation.id,
                useHintRect: false,
            } as TemplateDefinition);
            setIsDirty(true);
        } else if (e.type === 'update') {
            Annotations.update(e.annotation);
            if (selectedAnnotation?.id === e.annotation.id) {
                setSelectedAnnotation(e.annotation);
            }
            setIsDirty(true);
        } else if (e.type === 'remove') {
            Annotations.remove(e.annotation.id);
            if (selectedAnnotation?.id === e.annotation.id) {
                setSelectedAnnotation(null);
                Definitions.remove(e.annotation.id);
            }
            setIsDirty(true);
        }
    };

    const handleOpen = useCallback(async () => {
        // 如果有未保存的修改，显示确认对话框
        if (isDirty) {
            const result = await yesNo({
                title: '未保存的修改',
                text: '当前有未保存的修改，是否继续打开新图片？未保存的修改将会丢失。'
            });
            if (result === 'no') {
                return;
            }
        }

        try {
            const result = await openFileWFS({
                accept: 'image/*,.json',
                multiple: true,
            });

            const imageFile = result.files.find((f: FileResult) => f.file.type.startsWith('image/'));
            const jsonFile = result.files.find((f: FileResult) => f.file.name.endsWith('.json'));

            if (imageFile) {
                imageFileNameRef.current = imageFile.name;
                const dataUrl = await readFileAsDataURL(imageFile.file);
                loadImage(dataUrl, !jsonFile);
            }

            // 保存文件句柄
            if (jsonFile) {
                currentFileResult.current = jsonFile;
                try {
                    const metaData = await readFileAsJSON(jsonFile.file) as ImageMetaData;
                    load(metaData);
                } catch (error) {
                    console.error('Failed to parse JSON file:', error);
                    throw new Error('JSON文件格式错误，无法加载。');
                }
            }

            if (imageFile && jsonFile) {
                showToast('success', '加载成功', '已载入图片与 meta 数据');
            } else if (imageFile) {
                showToast('success', '加载成功', '已载入新图片');
            } else if (jsonFile) {
                showToast('success', '加载成功', '已载入 meta 数据');
            }
        } catch (error) {
            await yesNo({
                title: '错误',
                text: error instanceof Error ? error.message : '加载文件时发生错误'
            });
            showToast('danger', '加载失败', '无法加载文件');
        }
    }, [handleImageLoad, isDirty, yesNo, showToast, load]);

    const handleSave = useCallback(async () => {
        if (currentFileResult.current?.fileSystem !== 'wfs') {
            try {
                // 如果没有当前文件，尝试创建新文件
                const handle = await saveFileAsWFS(
                    toString(imageMetaData),
                    imageFileNameRef.current ? `${imageFileNameRef.current}.json` : 'metadata.json'
                );
                
                // 更新当前文件引用
                currentFileResult.current = {
                    file: await handle.getFile(),
                    name: (await handle.getFile()).name,
                    handle,
                    fileSystem: 'wfs'
                };
                
                setIsDirty(false);
                showToast('success', '保存成功', '文件已保存');
                return;
            } catch (error) {
                console.error('Failed to save file:', error);
                showToast('danger', '保存失败', '无法保存文件');
                return;
            }
        }

        try {
            const handle = await saveFileWFS(
                currentFileResult.current?.handle,
                toString(imageMetaData),
                imageFileNameRef.current ? `${imageFileNameRef.current}.json` : 'metadata.json'
            );

            // 更新文件句柄
            if (handle !== currentFileResult.current?.handle) {
                currentFileResult.current = {
                    file: await handle.getFile(),
                    name: (await handle.getFile()).name,
                    handle,
                    fileSystem: 'wfs'
                };
            }
            setIsDirty(false);
            showToast('success', '保存成功', '文件已保存');
        } catch (error) {
            console.error('Failed to save file:', error);
            showToast('danger', '保存失败', '无法保存文件');
        }
    }, [currentFileResult, imageMetaData, showToast]);

    const handleToolSelect = useCallback((id: string) => {
        setCurrentTool(STR_TO_TOOL[id]);
    }, [STR_TO_TOOL]);
    const handleToolClick = useCallback((id: string) => {
        if (id === 'open') {
            handleOpen();
        } else if (id === 'save') {
            handleSave();
        }
    }, [handleOpen, handleSave]);

    const handleAnnotationSelect = (annotation: Annotation | null) => {
        setSelectedAnnotation(annotation);
    };

    const handleDefinitionChange = (id: string, changes: Partial<TemplateDefinition>) => {
        Definitions.update({
            ...changes,
            annotationId: id
        });
        
        // 更新标注的提示文本
        const definition = imageMetaData.definitions[id];
        const displayName = changes.displayName || definition.displayName;
        const name = changes.name || definition.name;
        if (definition) {
            Annotations.update({
                id,
                _tip: <Tip>{displayName} ({name})</Tip>
            });
        }
    };

    useHotkey([
        {
            key: 's',
            ctrl: true,
            callback: handleSave
        },
        {
            key: 'v',
            single: true,
            callback: () => setCurrentTool(Tools.Drag)
        },
        {
            key: 't',
            single: true,
            callback: () => setCurrentTool(Tools.Template)
        },
        {
            key: 'b',
            single: true,
            callback: () => setCurrentTool(Tools.HintBox)
        },
        {
            key: 'delete',
            single: true,
            callback: () => {
                if (selectedAnnotation) {
                    handleAnnotationChange({
                        currentTool: EditorTool.Drag,
                        type: 'remove',
                        annotationType: 'rect',
                        annotation: selectedAnnotation
                    });
                    setSelectedAnnotation(null);
                }
            }
        }
    ]);

    const properties = usePropertyGridData(
        selectedAnnotation,
        imageMetaData.definitions,
        image,
        (imageUrl) => openModal(imageUrl, { imageRendering: 'pixelated' }),
        handleDefinitionChange,
        imageFileNameRef.current,
        imageMetaData.annotations,
        currentFileResult.current
    );

    return (
        <PageContainer>
            <SideToolBar
                tools={tools}
                selectedToolId={currentTool}
                onSelectTool={handleToolSelect}
                onClickTool={handleToolClick}
            />
            <EditorContainer>
                <DragArea onImageLoad={handleImageLoad}>
                    <ImageEditor
                        image={imageUrl}
                        tool={TOOL_TO_EDITOR_TOOL[currentTool]}
                        annotations={imageMetaData.annotations}
                        onAnnotationChanged={handleAnnotationChange}
                        onAnnotationSelected={handleAnnotationSelect}
                        enableMask
                        showCrosshair
                    />
                </DragArea>
            </EditorContainer>
            <PropertyContainer>
                <PropertyGrid properties={properties} />
            </PropertyContainer>
            {modal}
            {MessageBoxComponent}
            {ToastComponent}
        </PageContainer>
    );
};

export default ImageAnnotation;
