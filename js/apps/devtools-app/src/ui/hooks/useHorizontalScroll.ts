import { useRef, useEffect } from 'react';

export function useHorizontalScroll(multiplier = 1) {
  const elRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    const el = elRef.current;
    if (!el) return;

    const onWheel = (e: WheelEvent) => {
      // Prefer handling vertical motion to convert to horizontal scroll.
      // If horizontal delta dominates, let native behavior through.
      if (Math.abs(e.deltaY) === 0 || Math.abs(e.deltaY) < Math.abs(e.deltaX)) return;

      e.preventDefault();
      el.scrollLeft += e.deltaY * multiplier;
    };

    el.addEventListener('wheel', onWheel, { passive: false });
    return () => el.removeEventListener('wheel', onWheel);
  }, [multiplier]);

  return elRef;
}

export default useHorizontalScroll;
