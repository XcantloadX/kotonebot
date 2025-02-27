import { AnnotationComponentProps, Point } from './types';
import styled from '@emotion/styled';
import { PostionConvertor } from './ImageEditor';

const PointMarker = styled.div<{x: number; y: number; isNew?: boolean}>`
  position: absolute;
  width: 20px;
  height: 20px;
  transform: translate(${props => props.x - 10}px, ${props => props.y - 10}px);
  pointer-events: none;

  &::before {
    content: '';
    position: absolute;
    width: 100%;
    height: 100%;
    border-radius: 50%;
    background: rgba(0, 119, 255, 0.5);
    border: 2px solid #1298fe;
  }

  &::after {
    content: '';
    position: absolute;
    top: 50%;
    left: 50%;
    width: 6px;
    height: 6px;
    background: #1298fe;
    border-radius: 50%;
    transform: translate(-50%, -50%);
  }
`;

interface Props extends AnnotationComponentProps {
    Convertor: PostionConvertor;
}

export default function PointAnnotation({ annotation, Convertor }: Props) {
    if (annotation.type !== 'point') return null;
    
    const pos = Convertor.posImage2Container(annotation.data as Point);
    
    return (
        <PointMarker
            key={annotation.id}
            x={pos.x}
            y={pos.y}
        />
    );
} 