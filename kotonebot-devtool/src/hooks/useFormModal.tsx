import { useState, useCallback } from 'react';
import Modal from 'react-bootstrap/Modal';
import Button from 'react-bootstrap/Button';
import Form from 'react-bootstrap/Form';

export interface FormField {
  type: 'text' | 'number' | 'password' | 'email' | 'textarea';
  label: string;
  name: string;
  required?: boolean;
  defaultValue?: string;
  validator?: (value: string) => boolean | string;
  placeholder?: string;
}

interface FormModalProps {
  show: boolean;
  onHide: () => void;
  onSubmit: (formData: Record<string, string>) => void;
  title: string;
  fields: FormField[];
}

function FormModal({ show, onHide, onSubmit, title, fields }: FormModalProps) {
  const [formData, setFormData] = useState<Record<string, string>>(() => {
    const initialData: Record<string, string> = {};
    fields.forEach(field => {
      initialData[field.name] = field.defaultValue || '';
    });
    return initialData;
  });

  const [errors, setErrors] = useState<Record<string, string>>({});

  // 添加重置表单的函数
  const resetForm = useCallback(() => {
    const initialData: Record<string, string> = {};
    fields.forEach(field => {
      initialData[field.name] = field.defaultValue || '';
    });
    setFormData(initialData);
    setErrors({});
  }, [fields]);

  // 在 Modal 隐藏时重置表单
  const handleHide = () => {
    resetForm();
    onHide();
  };

  const handleChange = (name: string, value: string) => {
    setFormData(prev => ({ ...prev, [name]: value }));
    // 清除错误
    if (errors[name]) {
      setErrors(prev => {
        const newErrors = { ...prev };
        delete newErrors[name];
        return newErrors;
      });
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    
    // 验证表单
    const newErrors: Record<string, string> = {};
    
    fields.forEach(field => {
      const value = formData[field.name];
      
      // 必填项验证
      if (field.required && !value) {
        newErrors[field.name] = '此字段为必填项';
        return;
      }
      
      // 自定义验证
      if (field.validator && value) {
        const validationResult = field.validator(value);
        if (typeof validationResult === 'string') {
          newErrors[field.name] = validationResult;
        } else if (!validationResult) {
          newErrors[field.name] = '输入值无效';
        }
      }
    });
    
    if (Object.keys(newErrors).length > 0) {
      setErrors(newErrors);
      return;
    }
    
    onSubmit(formData);
    resetForm(); // 提交成功后也重置表单
  };

  return (
    <Modal show={show} onHide={handleHide}>
      <Form onSubmit={handleSubmit}>
        <Modal.Header closeButton>
          <Modal.Title>{title}</Modal.Title>
        </Modal.Header>
        <Modal.Body>
          {fields.map(field => (
            <Form.Group key={field.name} className="mb-3">
              <Form.Label>{field.label}</Form.Label>
              {field.type === 'textarea' ? (
                <Form.Control
                  as="textarea"
                  rows={3}
                  value={formData[field.name]}
                  onChange={e => handleChange(field.name, e.target.value)}
                  isInvalid={!!errors[field.name]}
                  placeholder={field.placeholder}
                />
              ) : (
                <Form.Control
                  type={field.type}
                  value={formData[field.name]}
                  onChange={e => handleChange(field.name, e.target.value)}
                  isInvalid={!!errors[field.name]}
                  placeholder={field.placeholder}
                />
              )}
              <Form.Control.Feedback type="invalid">
                {errors[field.name]}
              </Form.Control.Feedback>
            </Form.Group>
          ))}
        </Modal.Body>
        <Modal.Footer>
          <Button variant="secondary" onClick={handleHide}>
            取消
          </Button>
          <Button variant="primary" type="submit">
            确定
          </Button>
        </Modal.Footer>
      </Form>
    </Modal>
  );
}

export function useFormModal(fields: FormField[]) {
  const [show, setShow] = useState(false);
  const [resolveRef, setResolveRef] = useState<((value: Record<string, string> | null) => void) | null>(null);

  const handleHide = useCallback(() => {
    setShow(false);
    if (resolveRef) {
      resolveRef(null);
      setResolveRef(null);
    }
  }, [resolveRef]);

  const handleSubmit = useCallback((formData: Record<string, string>) => {
    setShow(false);
    if (resolveRef) {
      resolveRef(formData);
      setResolveRef(null);
    }
  }, [resolveRef]);

  const showModal = useCallback(async (title: string = '表单'): Promise<Record<string, string> | null> => {
    return new Promise(resolve => {
      setResolveRef(() => resolve);
      setShow(true);
    });
  }, []);

  const modal = (
    <FormModal
      show={show}
      onHide={handleHide}
      onSubmit={handleSubmit}
      title="表单"
      fields={fields}
    />
  );

  return {
    modal,
    show: showModal
  };
} 