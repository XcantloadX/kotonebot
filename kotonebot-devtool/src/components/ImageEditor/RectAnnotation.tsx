import { AnnotationComponentProps, RectPoints } from './types';
import RectBox from './RectBox';
import { PostionConvertor } from './ImageEditor';

interface Props extends AnnotationComponentProps {
    Convertor: PostionConvertor;
}

export default function RectAnnotation({ annotation, Convertor }: Props) {
    if (annotation.type !== 'rect') return null;
    
    return (
        <RectBox
            key={annotation.id}
            mode="move"
            rect={Convertor.rectImage2Container(annotation.data as RectPoints)}
            lineColor="white"
        />
    );
} 