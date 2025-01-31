import { Modal } from 'react-bootstrap';
import ImageViewer, { ImageViewerRef } from './ImageViewer';
import { useRef, useState } from 'react';
import styled from '@emotion/styled';

const ModalBackdrop = styled.div`
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(0, 0, 0, 0.4);
  z-index: 1040;
`;

const ToolBar = styled.div`
  position: absolute;
  bottom: 20px;
  left: 50%;
  transform: translateX(-50%);
  display: flex;
  gap: 10px;
  padding: 8px;
  background: rgba(0, 0, 0, 0.6);
  border-radius: 8px;
  z-index: 1;
`;

const ToolButton = styled.button`
  width: 40px;
  height: 40px;
  border: none;
  border-radius: 4px;
  background: transparent;
  color: white;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;

  &:hover {
    background: rgba(255, 255, 255, 0.1);
  }

  &:active {
    background: rgba(255, 255, 255, 0.2);
  }
`;

interface ImageViewerModalProps {
  show: boolean;
  onHide: () => void;
  image: string;
  imageRendering?: 'pixelated' | 'auto';
  title?: string;
}

function ImageViewerModal(props: ImageViewerModalProps) {
  const { show, onHide, image, imageRendering = 'auto', title } = props;
  const imageViewerRef = useRef<ImageViewerRef>(null);

  const handleZoomIn = () => {
    if (imageViewerRef.current) {
      const currentScale = imageViewerRef.current.scale;
      imageViewerRef.current.setScale(currentScale * 1.2);
    }
  };

  const handleZoomOut = () => {
    if (imageViewerRef.current) {
      const currentScale = imageViewerRef.current.scale;
      imageViewerRef.current.setScale(currentScale / 1.2);
    }
  };

  const handleResetZoom = () => {
    imageViewerRef.current?.reset('zoom');
  };

  const handleFit = () => {
    imageViewerRef.current?.fit();
  };

  return (
    <>
      {show && <ModalBackdrop />}
      <Modal 
        show={show} 
        onHide={onHide}
        size="xl"
        dialogClassName="modal-90w"
        centered
        style={{ zIndex: 1050 }}
      >
        <Modal.Header closeButton style={{ border: 'none' }}>
          {title && <Modal.Title>{title}</Modal.Title>}
        </Modal.Header>
        <Modal.Body className="p-0" style={{ position: 'relative' }}>
          <div style={{ width: '100%', height: 'calc(90vh - 56px)' }}>
            <ImageViewer
              ref={imageViewerRef}
              image={image}
              zoomable={true}
              movable={true}
              imageRendering={imageRendering}
            />
          </div>
          <ToolBar>
            <ToolButton onClick={handleZoomIn} title="放大">
              <i className="bi bi-zoom-in"></i>
            </ToolButton>
            <ToolButton onClick={handleZoomOut} title="缩小">
              <i className="bi bi-zoom-out"></i>
            </ToolButton>
            <ToolButton onClick={handleFit} title="适应容器">
              <i className="bi bi-aspect-ratio"></i>
            </ToolButton>
            <ToolButton onClick={handleResetZoom} title="重置缩放">
              <i className="bi bi-arrow-counterclockwise"></i>
            </ToolButton>
          </ToolBar>
        </Modal.Body>
      </Modal>
    </>
  );
}

interface ImageViewerModalOpenOptions {
  imageRendering?: 'pixelated' | 'auto';
}

export function useImageViewerModal(title?: string, options?: ImageViewerModalOpenOptions) {
  const [show, setShow] = useState(false);
  const [image, setImage] = useState<string>('');
  const [imageRendering, setImageRendering] = useState<'pixelated' | 'auto'>('auto');

  const openModal = (imageUrl: string, options?: ImageViewerModalOpenOptions) => {
    setImage(imageUrl);
    setImageRendering(options?.imageRendering || 'auto');
    setShow(true);
  };

  const closeModal = () => {
    setShow(false);
  };

  const modal = (
    <ImageViewerModal
      show={show}
      onHide={closeModal}
      image={image}
      imageRendering={imageRendering}
      title={title}
    />
  );

  return {
    modal,
    openModal,
    closeModal
  };
}

export default ImageViewerModal;
