import React, { useCallback, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { Modal } from 'react-bootstrap';

interface MessageBoxProps {
  title: string;
  text: string;
  onClose: (result: string) => void;
  type: 'yesno' | 'ok' | 'confirmcancel';
  show: boolean;
}


const MessageBoxComponent: React.FC<MessageBoxProps> = ({
  title,
  text,
  onClose,
  type,
  show
}) => {
  const handleClose = useCallback((result: string) => {
    onClose(result);
  }, [onClose]);

  const renderButtons = () => {
    switch (type) {
      case 'yesno':
        return (
          <>
            <button className="btn btn-primary" onClick={() => handleClose('yes')}>
              是
            </button>
            <button className="btn btn-secondary" onClick={() => handleClose('no')}>
              否
            </button>
          </>
        );
      case 'ok':
        return (
          <button className="btn btn-primary" onClick={() => handleClose('ok')}>
            确定
          </button>
        );
      case 'confirmcancel':
        return (
          <>
            <button className="btn btn-primary" onClick={() => handleClose('confirm')}>
              确认
            </button>
            <button className="btn btn-secondary" onClick={() => handleClose('cancel')}>
              取消
            </button>
          </>
        );
    }
  };

  return createPortal(
    <Modal show={show} onHide={() => handleClose('cancel')} centered>
      <Modal.Header closeButton>
        <Modal.Title>{title}</Modal.Title>
      </Modal.Header>
      <Modal.Body>{text}</Modal.Body>
      <Modal.Footer>
        {renderButtons()}
      </Modal.Footer>
    </Modal>,
    document.body
  );
};

interface MessageBoxOptions {
  title: string;
  text: string;
}

export function useMessageBox() {
  const [modalProps, setModalProps] = useState<Omit<MessageBoxProps, 'onClose'> | null>(null);
  const resolveRef = useRef<((value: string) => void) | null>(null);

  const showModal = useCallback((
    type: 'yesno' | 'ok' | 'confirmcancel',
    options: MessageBoxOptions
  ): Promise<string> => {
    return new Promise((resolve) => {
      resolveRef.current = resolve;
      setModalProps({
        type,
        title: options.title,
        text: options.text,
        show: true
      });
    });
  }, []);

  const handleClose = useCallback((result: string) => {
    setModalProps(prev => prev ? { ...prev, show: false } : null);
    // 等待动画结束后再resolve

      if (resolveRef.current) {
        resolveRef.current(result);
        resolveRef.current = null;
      }

  }, []);

  const yesNo = useCallback((options: MessageBoxOptions) => {
    return showModal('yesno', options) as Promise<'yes' | 'no'>;
  }, [showModal]);

  const ok = useCallback((options: MessageBoxOptions) => {
    return showModal('ok', options) as Promise<'ok'>;
  }, [showModal]);

  const confirmCancel = useCallback((options: MessageBoxOptions) => {
    return showModal('confirmcancel', options) as Promise<'confirm' | 'cancel'>;
  }, [showModal]);

  return {
    yesNo,
    ok,
    confirmCancel,
    MessageBoxComponent: modalProps ? (
      <MessageBoxComponent {...modalProps} onClose={handleClose} />
    ) : null
  };
}
