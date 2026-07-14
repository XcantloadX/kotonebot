import React from 'react';
import { Tooltip } from '@blueprintjs/core';
import { PrimaryGeometry } from '../../model/symbolIndex';
import { CropPreview, buildHoverPreviewUrl } from './CropPreview';

interface TooltipWithPreviewProps {
  imagePath: string;
  geometry?: PrimaryGeometry | null;
  children: React.ReactElement;
}

export const TooltipWithPreview: React.FC<TooltipWithPreviewProps> = ({
  imagePath,
  geometry,
  children,
}) => {
  const [ready, setReady] = React.useState(false);

  React.useEffect(() => {
    setReady(false);
    const url = buildHoverPreviewUrl(imagePath, geometry, 240);
    const img = new Image();
    img.onload = () => setReady(true);
    img.onerror = () => setReady(true);
    img.src = url;
    return () => {
      img.onload = null;
      img.onerror = null;
    };
  }, [imagePath, geometry]);

  if (!ready) {
    return children;
  }

  return (
    <Tooltip
      content={<CropPreview imagePath={imagePath} geometry={geometry} />}
      hoverOpenDelay={500}
      position="right"
    >
      {children}
    </Tooltip>
  );
};
