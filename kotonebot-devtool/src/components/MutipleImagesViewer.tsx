import React, { useCallback, useEffect, useRef, useState } from 'react';
import styled from '@emotion/styled';
import ImageViewer, { ImageViewerRef } from './ImageViewer';
import { css } from '@emotion/react';

export interface ImageGroup {
  mainIndex: number;
  images: string[];
}

interface MultipleImagesViewerProps {
  /** 当前组 */
  currentGroup: ImageGroup;
  /** 组数 */
  groupCount: number;
  /** 当前组索引 */
  groupIndex: number;
  /** 当前图片索引 */
  imageIndex: number;
  /** 跳转到指定组回调 */
  onGotoGroup: (groupIndex: number) => void;
  /** 跳转到指定图片回调 */
  onGotoImage: (imageIndex: number) => void;
}

const ViewerContainer = styled.div`
  height: 100%;
  display: flex;
  flex-direction: column;
`;

const MainContent = styled.div`
  flex: 1;
  min-height: 0;  /* 重要：防止内容溢出 */
  position: relative;
`;

const ControlsContainer = styled.div`
  padding: 10px;
  background-color: #f8f9fa;
  border-top: 1px solid #ddd;
`;

const Toolbar = styled.div`
  padding: 6px;
  text-align: center;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 20px;
  margin-bottom: 10px;
`;

const SliderContainer = styled.div`
  padding: 0 20px;
  margin-bottom: 10px;
`;

const Slider = styled.input`
  width: 100%;
`;

const NavigationControls = styled.div`
  display: flex;
  align-items: center;
  gap: 15px;
  justify-content: center;
`;

const ZoomControls = styled.div`
  display: flex;
  align-items: center;
  gap: 10px;
  & > span {
    margin: 0 10px;
  }
`;

const MultipleImagesViewer: React.FC<MultipleImagesViewerProps> = ({ 
  currentGroup,
  groupCount,
  groupIndex,
  imageIndex,
  onGotoGroup = () => {},
  onGotoImage = () => {},
}) => {
  const [isViewLocked, setIsViewLocked] = useState(false);
  const [scale, setScale] = useState(1.0);
  const imageViewerRef = useRef<ImageViewerRef>(null);


  // 处理缩放控制
  const handleZoomIn = () => {
    setScale((prev) => prev + 0.1);
    imageViewerRef.current?.setScale(scale + 0.1);
  };

  const handleZoomOut = () => {
    setScale((prev) => prev - 0.1);
    imageViewerRef.current?.setScale(scale - 0.1);
  };

  const handleResetZoom = () => {
    setScale(1);
    imageViewerRef.current?.reset('zoom');
  };

  const handleFit = () => {
    imageViewerRef.current?.fit();
    setScale(imageViewerRef.current?.scale || 1);
  };

  const handleUserMouseWheelZoom = (e: WheelEvent, scale: number) => {
    setScale(scale);
  };

  // 处理下载
  const handleDownload = useCallback(() => {
    const currentImages = currentGroup?.images || [];
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
    
    currentImages.forEach((url, index) => {
      const link = document.createElement('a');
      link.href = url;
      const fileName = currentImages.length > 1 
        ? `image_${groupIndex + 1}_${index + 1}_${timestamp}.png`
        : `image_${groupIndex + 1}_${timestamp}.png`;
      link.download = fileName;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    });
  }, [currentGroup, groupIndex]);

  // 处理滑块变化
  const handleSliderChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    console.log(e.target.value);
    onGotoGroup(parseInt(e.target.value));
  };

  // 处理视图锁定
  const handleViewLockChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setIsViewLocked(e.target.checked);
  };

  // 键盘快捷键
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) {
        return;
      }

      switch (e.key) {
        case 'ArrowLeft':
          onGotoGroup(groupIndex - 1);
          break;
        case 'ArrowRight':
          onGotoGroup(groupIndex + 1);
          break;
        case 'Home':
          onGotoGroup(0);
          break;
        case 'End':
          onGotoGroup(groupCount - 1);
          break;
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => {
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [groupCount, groupIndex, onGotoGroup]);

  const _currentGroup = currentGroup;
  const _currentImage = _currentGroup?.images?.[imageIndex];

  return (
    <ViewerContainer>
      <MainContent>
        {_currentImage && (
          <ImageViewer
            ref={imageViewerRef}
            image={_currentImage}
            zoomable={true}
            movable={true}
            keepTransforms={isViewLocked}
            onMouseWheelZoom={handleUserMouseWheelZoom}
          />
        )}
      </MainContent>

      <ControlsContainer>
        <Toolbar>
          <ZoomControls>
            <button 
              className="btn btn-outline-secondary btn-sm d-flex align-items-center gap-1" 
              onClick={handleZoomOut} 
              title="缩小"
            >
              <i className="bi bi-zoom-out" />
            </button>
            <span>{Math.round(scale * 100)}%</span>
            <button 
              className="btn btn-outline-secondary btn-sm d-flex align-items-center gap-1" 
              onClick={handleZoomIn} 
              title="放大"
            >
              <i className="bi bi-zoom-in" />
            </button>
            <button 
              className="btn btn-outline-secondary btn-sm d-flex align-items-center gap-1" 
              onClick={handleResetZoom} 
              title="重置缩放"
            >
              <i className="bi bi-arrow-counterclockwise" />
            </button>
            <button 
              className="btn btn-outline-secondary btn-sm d-flex align-items-center gap-1" 
              onClick={handleFit} 
              title="适应窗口"
            >
              <i className="bi bi-arrows-angle-contract" />
            </button>
          </ZoomControls>

          <button 
            className="btn btn-outline-secondary btn-sm d-flex align-items-center gap-1" 
            onClick={handleDownload} 
            title="下载图片组"
          >
            <i className="bi bi-download" />
          </button>

          <div className="form-check form-check-inline">
            <input
              className="form-check-input"
              type="checkbox"
              id="lockViewCheckbox"
              checked={isViewLocked}
              onChange={handleViewLockChange}
            />
            <label className="form-check-label" htmlFor="lockViewCheckbox">
              锁定视图
            </label>
          </div>

          <div css={css`display: flex;`}>
            <button
              className="btn btn-outline-secondary btn-sm d-flex align-items-center gap-1"
              onClick={() => {
                if (imageIndex > 0) {
                  onGotoImage(imageIndex - 1);
                }
              }}
              disabled={imageIndex <= 0}
              title="上一张图片"
            >
              <i className="bi bi-arrow-left-short" />
            </button>
            <span className="mx-2">
              {imageIndex + 1}/{ currentGroup?.images?.length }
            </span>
            <button
              className="btn btn-outline-secondary btn-sm d-flex align-items-center gap-1"
              onClick={() => {
                if (imageIndex < currentGroup?.images?.length - 1) {
                  onGotoImage(imageIndex + 1);
                }
              }}
              disabled={imageIndex >= currentGroup?.images?.length - 1}
              title="下一张图片"
            >
              <i className="bi bi-arrow-right-short" />
            </button>
          </div>
        </Toolbar>

        <SliderContainer>
          <Slider
            type="range"
            className="form-range"
            min={0}
            max={groupCount - 1}
            value={groupIndex}
            onChange={handleSliderChange}
          />
        </SliderContainer>

        <NavigationControls>
          <button
            className="btn btn-outline-secondary btn-sm d-flex align-items-center gap-1"
            onClick={() => onGotoGroup(0)}
            disabled={groupIndex <= 0}
            title="第一组"
          >
            <i className="bi bi-chevron-bar-left" />
          </button>
          <button
            className="btn btn-outline-secondary btn-sm d-flex align-items-center gap-1"
            onClick={() => onGotoGroup(groupIndex - 1)}
            disabled={groupIndex <= 0}
            title="上一组"
          >
            <i className="bi bi-chevron-left" />
          </button>
          <span>
            {groupIndex + 1} / {groupCount}
          </span>
          <button
            className="btn btn-outline-secondary btn-sm d-flex align-items-center gap-1"
            onClick={() => onGotoGroup(groupIndex + 1)}
            disabled={groupIndex >= groupCount - 1}
            title="下一组"
          >
            <i className="bi bi-chevron-right" />
          </button>
          <button
            className="btn btn-outline-secondary btn-sm d-flex align-items-center gap-1"
            onClick={() => onGotoGroup(groupCount - 1)}
            disabled={groupIndex >= groupCount - 1}
            title="最后一组"
          >
            <i className="bi bi-chevron-bar-right" />
          </button>
        </NavigationControls>
      </ControlsContainer>
    </ViewerContainer>
  );
};

export default MultipleImagesViewer;
