import React from 'react';
import styled from '@emotion/styled';

const DragAreaContainer = styled.div<{ isDragging: boolean }>`
  position: relative;
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: ${props => props.isDragging ? 'rgba(0, 0, 0, 0.05)' : 'transparent'};
  transition: background-color 0.2s;
`;

const DragOverlay = styled.div<{ isDragging: boolean }>`
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: rgba(255, 255, 255, 0.9);
  border: 2px dashed #ccc;
  pointer-events: none;
  opacity: ${props => props.isDragging ? 1 : 0};
  transition: opacity 0.2s;
  z-index: 1000;
`;

const DragText = styled.div`
  font-size: 1.2rem;
  color: #666;
`;

interface DragAreaProps {
  children?: React.ReactNode;
  onImageLoad?: (imageUrl: string) => void;
}

const DragArea: React.FC<DragAreaProps> = ({ children, onImageLoad }) => {
  const [isDragging, setIsDragging] = React.useState(false);

  const handleDragOver = React.useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  }, []);

  const handleDragLeave = React.useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  }, []);

  const handleDrop = React.useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);

    const files = Array.from(e.dataTransfer.files);
    const imageFile = files.find(file => file.type.startsWith('image/'));

    if (imageFile && onImageLoad) {
      const reader = new FileReader();
      reader.onload = (event) => {
        if (event.target?.result) {
          onImageLoad(event.target.result as string);
        }
      };
      reader.readAsDataURL(imageFile);
    }
  }, [onImageLoad]);

  return (
    <DragAreaContainer
      isDragging={isDragging}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
    >
      {children}
      <DragOverlay isDragging={isDragging}>
        <DragText>拖放图片到此处</DragText>
      </DragOverlay>
    </DragAreaContainer>
  );
};

export default DragArea;
