import React, { useCallback, useEffect, useState } from 'react';
import { createRoot } from 'react-dom/client';
import { Spinner } from 'react-bootstrap';
import styled from '@emotion/styled';

const SpinnerOverlay = styled.div`
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(255, 255, 255, 0.8);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  z-index: 9999;
`;

const SpinnerText = styled.div`
  margin-top: 1rem;
  color: #666;
  font-size: 0.9rem;
  white-space: pre-wrap;
`;

interface SpinnerComponentProps {
  message?: string;
  show: boolean;
}

const SpinnerComponent: React.FC<SpinnerComponentProps> = ({
  message,
  show
}) => {
  if (!show) return null;

  return (
    <SpinnerOverlay>
      <Spinner
        animation="border"
        variant="primary"
        style={{ width: '3rem', height: '3rem' }}
      />
      {message && <SpinnerText>{message}</SpinnerText>}
    </SpinnerOverlay>
  );
};

// 创建一个单例来管理 spinner root
const createSpinnerRoot = () => {
  const containerId = 'fullscreen-spinner-root';
  let container = document.getElementById(containerId);
  
  if (!container) {
    container = document.createElement('div');
    container.id = containerId;
    document.body.appendChild(container);
  }
  
  return createRoot(container);
};

let spinnerRoot: ReturnType<typeof createRoot> | null = null;

export function useFullscreenSpinner() {
  const [spinnerProps, setSpinnerProps] = useState<SpinnerComponentProps>({
    show: false,
    message: undefined
  });

  // 在第一次使用时创建 root
  useEffect(() => {
    if (!spinnerRoot) {
      spinnerRoot = createSpinnerRoot();
    }
    
    // 在组件卸载时，如果没有其他组件使用 spinner，则清理 root
    return () => {
      if (spinnerRoot && !spinnerProps.show) {
        // 使用 requestAnimationFrame 确保在下一帧进行卸载
        requestAnimationFrame(() => {
          const container = document.getElementById('fullscreen-spinner-root');
          if (container) {
            spinnerRoot?.unmount();
            container.remove();
            spinnerRoot = null;
          }
        });
      }
    };
  }, [spinnerProps.show]);

  // 当 props 改变时更新 root
  useEffect(() => {
    spinnerRoot?.render(<SpinnerComponent {...spinnerProps} />);
  }, [spinnerProps]);

  const show = useCallback((message?: string) => {
    setSpinnerProps({
      show: true,
      message
    });
  }, []);

  const hide = useCallback(() => {
    setSpinnerProps(prev => ({ ...prev, show: false }));
  }, []);

  return {
    show,
    hide
  };
}
