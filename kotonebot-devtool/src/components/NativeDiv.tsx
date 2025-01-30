import { HTMLAttributes, forwardRef, useEffect, useRef } from 'react';

interface NativeDivProps extends HTMLAttributes<HTMLDivElement> {
  onNativeMouseEnter?: (e: MouseEvent) => void;
  onNativeMouseMove?: (e: MouseEvent) => void;
  onNativeMouseLeave?: (e: MouseEvent) => void;
  onNativeMouseDown?: (e: MouseEvent) => void;
  onNativeClick?: (e: MouseEvent) => void;
}

/**
 * 对原生 div 元素的封装。
 * 
 * 添加了下面这些事件：
 * * onNativeMouseEnter
 * * onNativeMouseMove
 * * onNativeMouseLeave
 * * onNativeMouseDown
 * * onNativeClick
 * 
 * 这些事件都是对原生 DOM 事件的封装。
 */
const NativeDiv = forwardRef<HTMLDivElement, NativeDivProps>((props, ref) => {
  const {
    onNativeMouseEnter,
    onNativeMouseMove,
    onNativeMouseLeave,
    onNativeMouseDown,
    onNativeClick,
    ...restProps
  } = props;

  const elementRef = useRef<HTMLDivElement | null>(null);
  if (ref) {
    if (typeof ref === 'function') {
      ref(elementRef.current);
    } else {
      ref.current = elementRef.current;
    }
  }

  useEffect(() => {
    const element = elementRef.current;
    if (!element) return;

    if (onNativeMouseEnter)
      element.addEventListener('mouseenter', onNativeMouseEnter);
    if (onNativeMouseMove)
      element.addEventListener('mousemove', onNativeMouseMove);
    if (onNativeMouseLeave)
      element.addEventListener('mouseleave', onNativeMouseLeave);
    if (onNativeMouseDown)
      element.addEventListener('mousedown', onNativeMouseDown);
    if (onNativeClick)
      element.addEventListener('click', onNativeClick);

    return () => {
      if (onNativeMouseEnter)
        element.removeEventListener('mouseenter', onNativeMouseEnter);
      if (onNativeMouseMove)
        element.removeEventListener('mousemove', onNativeMouseMove);
      if (onNativeMouseLeave)
        element.removeEventListener('mouseleave', onNativeMouseLeave);
      if (onNativeMouseDown)
        element.removeEventListener('mousedown', onNativeMouseDown);
      if (onNativeClick)
        element.removeEventListener('click', onNativeClick);
    };
  }, [onNativeMouseEnter, onNativeMouseMove, onNativeMouseLeave, onNativeClick]);

  return <div ref={elementRef} {...restProps} />;
});

NativeDiv.displayName = 'NativeDiv';
export default NativeDiv;