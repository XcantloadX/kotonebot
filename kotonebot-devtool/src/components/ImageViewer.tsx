import React, { forwardRef, useCallback, useEffect, useImperativeHandle, useRef, useState } from 'react';
import styled from '@emotion/styled';

interface ImageViewerProps {
  /** 图片地址 */
  image: string;
  /** 是否可缩放 */
  zoomable?: boolean;
  /** 是否可移动 */
  movable?: boolean;
  /** 最小缩放比例 */
  minZoomScale?: number;
  /** 最大缩放比例 */
  maxZoomScale?: number;
  /** 缩放步长 */
  zoomStep?: number;
  /** 滚轮缩放事件 */
  onMouseWheelZoom?: (e: WheelEvent, scale: number) => void;
  /** 是否保持变换状态（缩放和位移） */
  keepTransforms?: boolean;
}

export interface ImageViewerRef {
  reset: (type?: 'zoom' | 'position' | 'all') => void;
  setScale: (scale: number) => void;
  scale: number;
  fit: () => void;
}

const ViewerContainer = styled.div`
  height: 100%;
  border: 1px solid #ddd;
  padding: 20px;
  display: flex;
  flex-direction: column;
`;

const ImageContainer = styled.div`
  flex: 1;
  border: 1px solid #eee;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  position: relative;
`;

interface StyledImageProps {
  withAnimation?: boolean;
}

const StyledImage = styled.img<StyledImageProps>`
  max-width: none;
  max-height: none;
  transform-origin: center center;
  cursor: grab;
  user-select: none;
  position: relative;
  transition: ${(props: StyledImageProps) => props.withAnimation ? 'transform 0.2s ease-out' : 'none'};

  &.dragging {
    cursor: grabbing;
    transition: none;
  }
`;

const ImageViewer = forwardRef<ImageViewerRef, ImageViewerProps>(
  ({ 
    image, 
    zoomable: scalable = true, 
    movable = true,
    minZoomScale: minScale = 0.1,
    maxZoomScale: maxScale = 5.0,
    zoomStep = 0.1,
    onMouseWheelZoom,
    keepTransforms = false,
  }, ref) => {
    const [scale, setScale] = useState(1.0);
    const [translateX, setTranslateX] = useState(0);
    const [translateY, setTranslateY] = useState(0);
    const [isDragging, setIsDragging] = useState(false);
    const [useAnimation, setUseAnimation] = useState(false);
    
    const startPosRef = useRef({ x: 0, y: 0 });
    const imageRef = useRef<HTMLImageElement>(null);
    const containerRef = useRef<HTMLDivElement>(null);

    // 重置视图
    const reset = (type: 'zoom' | 'position' | 'all' = 'all') => {
      setUseAnimation(true);
      if (type === 'zoom' || type === 'all') {
        setScale(1.0);
      }
      if (type === 'position' || type === 'all') {
        setTranslateX(0);
        setTranslateY(0);
      }
    };

    // 适应容器大小
    const fit = () => {
      if (!imageRef.current || !containerRef.current) return;
      
      const container = containerRef.current;
      const img = imageRef.current;
      
      const containerRatio = container.clientWidth / container.clientHeight;
      const imageRatio = img.naturalWidth / img.naturalHeight;
      
      let fitScale;
      if (imageRatio > containerRatio) {
        fitScale = container.clientWidth / img.naturalWidth * 0.9;
      } else {
        fitScale = container.clientHeight / img.naturalHeight * 0.9;
      }
      
      setUseAnimation(false);
      setScale(fitScale);
      setTranslateX(0);
      setTranslateY(0);
    };

    // 设置缩放
    const setScaleWithLimits = useCallback((newScale: number, withAnimation = false) => {
      if (!scalable) return;
      const limitedScale = Math.min(Math.max(newScale, minScale), maxScale);
      setUseAnimation(withAnimation);
      setScale(limitedScale);
    }, [scalable, minScale, maxScale]);

    // 暴露方法给父组件
    useImperativeHandle(ref, () => ({
      reset,
      setScale: (scale: number) => setScaleWithLimits(scale, true),
      get scale() {
        return scale;
      },
      fit
    }));

    // ===== 事件 =====
    // 处理鼠标按下事件
    const handleMouseDown = (e: React.MouseEvent) => {
      if (!movable) return;
      setIsDragging(true);
      startPosRef.current = {
        x: e.clientX - translateX,
        y: e.clientY - translateY
      };
    };

    // 处理鼠标移动事件
    const handleMouseMove = (e: React.MouseEvent) => {
      if (!isDragging || !movable) return;
      setUseAnimation(false);
      setTranslateX(e.clientX - startPosRef.current.x);
      setTranslateY(e.clientY - startPosRef.current.y);
    };

    // 处理鼠标松开事件
    const handleMouseUp = () => {
      setIsDragging(false);
    };

    // 处理滚轮缩放
    const handleWheel = useCallback((e: WheelEvent) => {
      if (!scalable) return;
      e.preventDefault();
      const delta = e.deltaY;
      setScaleWithLimits(scale + (delta > 0 ? -zoomStep : zoomStep), true);
      onMouseWheelZoom?.(e, scale + (delta > 0 ? -zoomStep : zoomStep));
    }, [scalable, scale, setScaleWithLimits, zoomStep, onMouseWheelZoom]);

    // 图片加载完成后自动适应容器大小
    const handleImageLoad = () => {
      if (!keepTransforms)
        fit();
    };

    // 监听
    useEffect(() => {
      const handleGlobalMouseUp = () => {
        if (isDragging) {
          setIsDragging(false);
        }
      };
      document.addEventListener('mouseup', handleGlobalMouseUp);
      return () => {
        document.removeEventListener('mouseup', handleGlobalMouseUp);
      };
    }, [isDragging]);
    useEffect(() => {
        if (!containerRef.current) return;
        const container = containerRef.current;
        container.addEventListener('wheel', handleWheel, { passive: false });
        return () => {
            container.removeEventListener('wheel', handleWheel);
        };
    }, [handleWheel]);

    // ===== JSX =====
    return (
      <ViewerContainer>
        <ImageContainer
          ref={containerRef}
          onMouseMove={handleMouseMove}
          onMouseUp={handleMouseUp}
        >
          <StyledImage
            ref={imageRef}
            src={image}
            onLoad={handleImageLoad}
            onMouseDown={handleMouseDown}
            onDragStart={(e: React.DragEvent<HTMLImageElement>) => e.preventDefault()}
            className={isDragging ? 'dragging' : ''}
            withAnimation={useAnimation}
            style={{
              transform: `translate(${translateX}px, ${translateY}px) scale(${scale})`
            }}
          />
        </ImageContainer>
      </ViewerContainer>
    );
  }
);

export default ImageViewer;
