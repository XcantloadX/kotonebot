import { HTMLAttributes, forwardRef, useEffect, useRef } from 'react';

interface NativeDivProps extends HTMLAttributes<HTMLDivElement> {
  onNativeMouseEnter?: (e: MouseEvent) => void;
  onNativeMouseMove?: (e: MouseEvent) => void;
  onNativeMouseLeave?: (e: MouseEvent) => void;
  onNativeMouseDown?: (e: MouseEvent) => void;
  onNativeClick?: (e: MouseEvent) => void;
  onNativeKeyDown?: (e: KeyboardEvent) => void;
  onNativeKeyUp?: (e: KeyboardEvent) => void;
  onNativeMouseWheel?: (e: WheelEvent) => void;
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
 * * onNativeKeyDown
 * * onNativeKeyUp
 * * onNativeMouseWheel
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
    onNativeKeyDown,
    onNativeKeyUp,
    onNativeMouseWheel,
    ...restProps
  } = props;

  const elementRef = useRef<HTMLDivElement | null>(null);


  useEffect(() => {
    const element = elementRef.current;
    if (!element) return;
    if (ref) {
      if (typeof ref === 'function') {
        ref(elementRef.current);
      } else {
        ref.current = elementRef.current;
      }
    }

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
    if (onNativeKeyDown)
      element.addEventListener('keydown', onNativeKeyDown);
    if (onNativeKeyUp)
      element.addEventListener('keyup', onNativeKeyUp);
    if (onNativeMouseWheel)
      element.addEventListener('wheel', onNativeMouseWheel);

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
      if (onNativeKeyDown)
        element.removeEventListener('keydown', onNativeKeyDown);
      if (onNativeKeyUp)
        element.removeEventListener('keyup', onNativeKeyUp);
      if (onNativeMouseWheel)
        element.removeEventListener('wheel', onNativeMouseWheel);
    };
  }, [onNativeMouseEnter, onNativeMouseMove, onNativeMouseLeave, onNativeClick, onNativeKeyDown, onNativeKeyUp, onNativeMouseWheel]);

  return <div ref={elementRef} {...restProps} />;
});

NativeDiv.displayName = 'NativeDiv';
export default NativeDiv;