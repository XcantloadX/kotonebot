import React, { useCallback, useState } from 'react';
import styled from '@emotion/styled';
import { registerToolPlugins } from './tools/plugins';
import { toolRegistry } from './tools/registry';
import DynamicToolBar, { DRAG_TOOL_ID } from './components/ToolBar/DynamicToolBar';
import PropertyGrid from '../../components/PropertyGrid';
import { Tool as EditorTool } from '../../components/ImageEditor/types';
import useImageMetaData from '../../hooks/useImageMetaData';
import { useImageViewerModal } from '../../components/ImageViewerModal';
import { useMessageBox } from '../../hooks/useMessageBox';
import { useToast } from '../../components/ToastMessage';
import NativeDiv from '../../components/NativeDiv';
import useHotkey from '../../hooks/useHotkey';
import { useFileOperations } from './hooks/useFileOperations';
import { useAnnotationManager } from './hooks/useAnnotationManager';
import { useToolManager } from './hooks/useToolManager';
import { useImage } from './hooks/useImage';
import { usePropertyGridData } from './hooks/usePropertyGridData';
import ImageCanvas from './components/ImageCanvas/ImageCanvas';

// Register all tool plugins before the component mounts
registerToolPlugins();

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
  overflow-y: auto;
`;

const ImageAnnotation: React.FC = () => {
    const [isDirty, setIsDirty] = useState(false);
    const [imageFileName, setImageFileName] = useState<string>('');
    const [imageUrl, setImageUrl] = useState<string>('');
    
    const image = useImage(imageUrl);
    const { imageMetaData, Definitions, Annotations, clear, load, toString } = useImageMetaData();
    const { currentTool, selectTool, setCurrentTool } = useToolManager();
    
    const { 
        selectedAnnotation, 
        handleAnnotationChange, 
        handleAnnotationSelect, 
        handleDefinitionChange, 
        deleteSelectedAnnotation 
    } = useAnnotationManager({
        imageMetaData,
        Annotations,
        Definitions,
        currentTool,
        onDirty: () => setIsDirty(true),
    });

    const { open, save, drop, currentFile } = useFileOperations({
        isDirty,
        imageMetaData,
        toString,
        onLoad: (metaData, newImageUrl, newFileName) => {
            load(metaData);
            if (newImageUrl) setImageUrl(newImageUrl);
            if (newFileName) setImageFileName(newFileName);
            setIsDirty(false);
        },
        onClear: () => {
            clear();
            handleAnnotationSelect(null);
            setIsDirty(false);
        },
        onSetImageUrl: (newImageUrl, newFileName) => {
            setImageUrl(newImageUrl);
            setImageFileName(newFileName);
        },
    });

    const { modal, openModal } = useImageViewerModal('裁剪预览');
    const { MessageBoxComponent } = useMessageBox();
    const { ToastComponent } = useToast();

    const handleToolClick = useCallback((id: string) => {
        if (id === 'open') open();
        else if (id === 'save') save();
    }, [open, save]);

    useHotkey([
        { key: 's', ctrl: true, callback: save },
        { key: 'v', single: true, callback: () => setCurrentTool(DRAG_TOOL_ID) },
        { key: 't', single: true, callback: () => setCurrentTool('template') },
        { key: 'b', single: true, callback: () => setCurrentTool('hint-box') },
        { key: 'p', single: true, callback: () => setCurrentTool('hint-point') },
        { key: 'delete', single: true, callback: deleteSelectedAnnotation }
    ]);

    const properties = usePropertyGridData(selectedAnnotation, imageMetaData.definitions, image, (url) => openModal(url, { imageRendering: 'pixelated' }), handleDefinitionChange, imageFileName, imageMetaData.annotations, currentFile);
    const editorTool = toolRegistry.get(currentTool)?.editorTool || EditorTool.Drag;

    const definition = selectedAnnotation ? imageMetaData.definitions[selectedAnnotation.id] : null;
    const toolPlugin = definition ? toolRegistry.get(definition.type) : null;
    const ToolProperties = toolPlugin?.PropertiesComponent;

    return (
        <PageContainer>
            <DynamicToolBar selectedToolId={currentTool} onSelectTool={selectTool} onClickTool={handleToolClick} />
            <EditorContainer>
                <ImageCanvas
                    imageUrl={imageUrl}
                    editorTool={editorTool}
                    annotations={imageMetaData.annotations}
                    onAnnotationChanged={handleAnnotationChange}
                    onAnnotationSelected={handleAnnotationSelect}
                    onImageDrop={drop}
                />
            </EditorContainer>
            <PropertyContainer>
                <PropertyGrid properties={properties} />
                {ToolProperties && definition && <ToolProperties definition={definition} onUpdate={(changes) => handleDefinitionChange(definition.annotationId, changes)} />}
            </PropertyContainer>
            {modal}
            {MessageBoxComponent}
            {ToastComponent}
        </PageContainer>
    );
};

export default ImageAnnotation;