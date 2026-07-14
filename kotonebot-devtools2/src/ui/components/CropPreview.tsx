import React from 'react';
import { Spinner } from '@blueprintjs/core';
import { PrimaryGeometry } from '../../model/symbolIndex';

export function buildHoverPreviewUrl(imagePath: string, geometry: PrimaryGeometry | null | undefined, size: number): string {
  const base = `/api/image/hover_preview?path=${encodeURIComponent(imagePath)}&size=${size}`;

  if (!geometry) {
    return `/api/image/thumbnail?path=${encodeURIComponent(imagePath)}&size=${size}`;
  }

  if (geometry.kind === 'point') {
    const half = Math.round(size * 0.4);
    const x1 = geometry.x - half;
    const y1 = geometry.y - half;
    const x2 = geometry.x + half;
    const y2 = geometry.y + half;
    return `${base}&x1=${x1}&y1=${y1}&x2=${x2}&y2=${y2}`;
  }

  return `${base}&x1=${geometry.x1}&y1=${geometry.y1}&x2=${geometry.x2}&y2=${geometry.y2}`;
}

interface CropPreviewProps {
  imagePath: string;
  geometry?: PrimaryGeometry | null;
  size?: number;
}

export const CropPreview: React.FC<CropPreviewProps> = ({
  imagePath,
  geometry,
  size = 240,
}) => {
  const [loaded, setLoaded] = React.useState(false);
  const [loadError, setLoadError] = React.useState(false);
  const src = buildHoverPreviewUrl(imagePath, geometry, size);

  React.useEffect(() => {
    setLoaded(false);
    setLoadError(false);
    const img = new Image();
    img.onload = () => setLoaded(true);
    img.onerror = () => setLoadError(true);
    img.src = src;
    return () => {
      img.onload = null;
      img.onerror = null;
    };
  }, [src]);

  const containerStyle: React.CSSProperties = {
    width: size,
    height: Math.round(size * 0.6),
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    borderRadius: 4,
    overflow: 'hidden',
  };

  if (loadError) {
    return (
      <div style={{ ...containerStyle, color: '#8a9ba8', fontSize: 12 }}>
        Failed to load preview
      </div>
    );
  }

  if (!loaded) {
    return (
      <div style={containerStyle}>
        <Spinner size={20} />
      </div>
    );
  }

  return (
    <div style={containerStyle}>
      <img
        src={src}
        alt=""
        style={{
          display: 'block',
          maxWidth: '100%',
          maxHeight: '100%',
        }}
      />
    </div>
  );
};
