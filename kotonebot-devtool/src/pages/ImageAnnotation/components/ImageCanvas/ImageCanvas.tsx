import React from 'react';
import DragArea from '../../DragArea';
import ImageEditor, { AnnotationChangedEvent } from '../../../../components/ImageEditor/ImageEditor';
import { Annotation, Tool as EditorTool } from '../../../../components/ImageEditor/types';
import { FileResult } from '../../../../utils/fileUtils';

interface ImageCanvasProps {
    imageUrl: string;
    editorTool: EditorTool;
    annotations: Annotation[];
    onAnnotationChanged: (e: AnnotationChangedEvent) => void;
    onAnnotationSelected: (annotation: Annotation | null) => void;
    onImageDrop: (result: FileResult) => Promise<void>;
}

const ImageCanvas: React.FC<ImageCanvasProps> = (props) => {
    return (
        <DragArea onImageLoad={props.onImageDrop}>
            <ImageEditor
                image={props.imageUrl}
                tool={props.editorTool}
                annotations={props.annotations}
                onAnnotationChanged={props.onAnnotationChanged}
                onAnnotationSelected={props.onAnnotationSelected}
                enableMask
                showCrosshair
            />
        </DragArea>
    );
};

export default ImageCanvas;
