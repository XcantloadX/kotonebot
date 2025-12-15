import { useState, useCallback } from 'react';
import { Annotation } from '../../../components/ImageEditor/types';
import { Definition, ImageMetaData } from '../types/definitions';
import { AnnotationChangedEvent } from '../../../components/ImageEditor/ImageEditor';
import { useToast } from '../../../components/ToastMessage';
import { toolRegistry } from '../tools/registry';
import useImageMetaData from '../../../hooks/useImageMetaData';
import { Tip } from '../components/Tip';

export interface UseAnnotationManagerProps {
    imageMetaData: ImageMetaData;
    Annotations: ReturnType<typeof useImageMetaData>['Annotations'];
    Definitions: ReturnType<typeof useImageMetaData>['Definitions'];
    currentTool: string;
    onDirty: () => void;
}

export function useAnnotationManager({
    imageMetaData,
    Annotations,
    Definitions,
    currentTool,
    onDirty,
}: UseAnnotationManagerProps) {
    const [selectedAnnotation, setSelectedAnnotation] = useState<Annotation | null>(null);
    const { showToast } = useToast();

    const handleAnnotationChange = useCallback((e: AnnotationChangedEvent) => {
        if (e.type === 'add') {
            const plugin = toolRegistry.get(currentTool);
            if (!plugin) {
                showToast('danger', '错误', `无法识别的标注工具: ${currentTool}`);
                return;
            }
            const definition = plugin.createDefinition(e.annotation);
            Annotations.add(e.annotation);
            Definitions.add(definition);
            onDirty();
        } else if (e.type === 'update') {
            Annotations.update(e.annotation);
            if (selectedAnnotation?.id === e.annotation.id) {
                setSelectedAnnotation(e.annotation);
            }
            onDirty();
        } else if (e.type === 'remove') {
            Annotations.remove(e.annotation.id);
            if (selectedAnnotation?.id === e.annotation.id) {
                setSelectedAnnotation(null);
                Definitions.remove(e.annotation.id);
            }
            onDirty();
        }
    }, [currentTool, Annotations, Definitions, selectedAnnotation, showToast, onDirty]);

    const handleAnnotationSelect = useCallback((annotation: Annotation | null) => {
        setSelectedAnnotation(annotation);
    }, []);

    const handleDefinitionChange = useCallback((id: string, changes: Partial<Definition>) => {
        Definitions.update({ ...changes, annotationId: id });
        const definition = imageMetaData.definitions[id];
        if (definition) {
            const displayName = changes.displayName || definition.displayName;
            const name = changes.name || definition.name;
            Annotations.update({ id, _tip: <Tip>{displayName} ({name})</Tip> });
        }
        onDirty();
    }, [Definitions, Annotations, imageMetaData.definitions, onDirty]);
    
    const deleteSelectedAnnotation = useCallback(() => {
        if (selectedAnnotation) {
            handleAnnotationChange({
                type: 'remove',
                annotation: selectedAnnotation,
                currentTool: 'drag',
                annotationType: selectedAnnotation.type,
            });
        }
    }, [selectedAnnotation, handleAnnotationChange]);

    return {
        selectedAnnotation,
        handleAnnotationChange,
        handleAnnotationSelect,
        handleDefinitionChange,
        deleteSelectedAnnotation,
    };
}
