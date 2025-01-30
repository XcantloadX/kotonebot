import { RectPoints } from "./types";
import styled from '@emotion/styled';

const MaskContainer = styled.div`
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
`;

interface RectMaskProps {
  rects: RectPoints[];
  alpha?: number;
  transition?: boolean;
}

function RectMask({ rects, alpha = 0.5, transition = false }: RectMaskProps) {
  return (
    <MaskContainer>
      <svg width="100%" height="100%" style={{ position: 'absolute' }}>
        <defs>
          <mask id="rectMask">
            {/* 首先创建一个黑色背景（完全遮罩） */}
            <rect x="0" y="0" width="100%" height="100%" fill="white" />
            
            {/* 然后在矩形区域创建白色区域（透明） */}
            {rects.map((rect, index) => (
              <rect
                key={index}
                x={rect.x1}
                y={rect.y1}
                width={rect.x2 - rect.x1}
                height={rect.y2 - rect.y1}
                fill="black"
                // style={transition ? { transition: 'all 0.1s ease-in-out' } : undefined}
              />
            ))}
          </mask>
        </defs>
        
        {/* 使用遮罩的矩形 */}
        <rect
          x="0"
          y="0"
          width="100%"
          height="100%"
          fill={`rgba(0, 0, 0, ${alpha})`}
          mask="url(#rectMask)"
          style={transition ? { transition: 'fill 0.2s ease-in-out' } : undefined}
        />
      </svg>
    </MaskContainer>
  );
}

export default RectMask;
