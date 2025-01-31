import React, { useState, useCallback } from 'react';
import Toast from 'react-bootstrap/Toast';
import ToastContainer from 'react-bootstrap/ToastContainer';
import styled from '@emotion/styled';

// 定义消息类型
export type ToastType = 'success' | 'danger' | 'info' | 'warning';

// 定义单个消息的数据结构
export interface ToastMessage {
  id: string;
  type: ToastType;
  title: string;
  message: string;
  duration?: number;
}

// 定义 Hook 返回的数据结构
export interface ToastHook {
  showToast: (type: ToastType, title: string, message: string, duration?: number) => void;
  ToastComponent: React.ReactNode;
}

// 样式化的 Toast 容器
const StyledToastContainer = styled(ToastContainer)`
  z-index: 9999;
  position: fixed;
  left: 50%;
  transform: translateX(-50%);
`;

// 自定义 Hook 用于管理 Toast 消息
export const useToast = (): ToastHook => {
  const [toasts, setToasts] = useState<ToastMessage[]>([]);

  // 移除指定 ID 的消息
  const removeToast = useCallback((id: string) => {
    setToasts(prev => prev.filter(toast => toast.id !== id));
  }, []);

  // 显示新消息
  const showToast = useCallback((
    type: ToastType,
    title: string,
    message: string,
    duration: number = 3000
  ) => {
    const id = Math.random().toString(36).substr(2, 9);
    setToasts(prev => [...prev, { id, type, title, message, duration }]);
  }, []);

  // 渲染 Toast 组件
  const ToastComponent = (
    <StyledToastContainer position="top-center" className="p-3">
      {toasts.map(toast => (
        <Toast
          key={toast.id}
          onClose={() => removeToast(toast.id)}
          show={true}
          delay={toast.duration}
          autohide
          bg={toast.type}
          className="mb-2"
        >
          <Toast.Header closeButton>
            <strong className="me-auto">{toast.title}</strong>
          </Toast.Header>
          <Toast.Body className='text-white'>
            {toast.message}
          </Toast.Body>
        </Toast>
      ))}
    </StyledToastContainer>
  );

  return {
    showToast,
    ToastComponent
  };
};
