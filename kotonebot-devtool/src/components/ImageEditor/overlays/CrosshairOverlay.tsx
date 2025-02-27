import { EditorOverlay, OverlayProps } from '../core/types';
import { Tool } from '../types';
import styled from '@emotion/styled';
import NativeDiv from '../../NativeDiv';
import { useState, useEffect } from 'react';

const CrosshairLine = styled(NativeDiv)<{ isVertical?: boolean; position: number }>`
  position: absolute;
  background-color: rgba(255, 255, 255, 0);
  border: none;
  ${props => props.isVertical
    ? `
      height: 100%;
      width: 0;
      left: ${props.position}px;
      border-left: 2px dashed rgba(255, 255, 255, 1);
    `
    : `
      width: 100%;
      height: 0;
      top: ${props.position}px;
      border-top: 2px dashed rgba(255, 255, 255, 1);
    `
  }
  pointer-events: none;
`;

const CrosshairComponent: React.FC<OverlayProps> = ({ editorProps, tool, containerRef }) => {
  const [mousePosition, setMousePosition] = useState({ x: 0, y: 0 });

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const handleMouseMove = (e: MouseEvent) => {
      const rect = container.getBoundingClientRect();
      setMousePosition({
        x: e.clientX - rect.left,
        y: e.clientY - rect.top
      });
    };

    container.addEventListener('mousemove', handleMouseMove as EventListener);
    
    return () => {
      container.removeEventListener('mousemove', handleMouseMove as EventListener);
    };
  }, [containerRef]);

  if (!editorProps.showCrosshair || tool !== Tool.Rect) {
    return null;
  }

  return (
    <>
      <CrosshairLine isVertical position={mousePosition.x} />
      <CrosshairLine position={mousePosition.y} />
    </>
  );
};

export const CrosshairOverlay: EditorOverlay = {
  name: 'crosshair',
  zIndex: 20,
  component: CrosshairComponent
};

export default CrosshairOverlay; 