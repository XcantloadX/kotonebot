import React, { useEffect, useMemo, useRef, useState } from "react";
import { useAppStore } from "./state";

export const FocusSpotlightOverlay: React.FC = () => {
  const spotlight = useAppStore((s) => s.focusSpotlight);
  const clearFocusSpotlight = useAppStore((s) => s.clearFocusSpotlight);
  const [renderedId, setRenderedId] = useState<string | null>(null);
  const [opacity, setOpacity] = useState(0);
  const [holeRadius, setHoleRadius] = useState(0);
  const timersRef = useRef<number[]>([]);
  const rafRef = useRef<number | null>(null);
  const easeInOutCubic = (t: number): number => {
    if (t < 0.5) {
      return 4 * t * t * t;
    }
    return 1 - Math.pow(-2 * t + 2, 3) / 2;
  };

  useEffect(() => {
    if (rafRef.current !== null) {
      window.cancelAnimationFrame(rafRef.current);
      rafRef.current = null;
    }
    for (const timer of timersRef.current) {
      window.clearTimeout(timer);
    }
    timersRef.current = [];

    if (!spotlight) {
      setRenderedId(null);
      return;
    }

    setRenderedId(spotlight.id);
    setOpacity(0);
    const maxDx = Math.max(spotlight.centerScreen.x, window.innerWidth - spotlight.centerScreen.x);
    const maxDy = Math.max(spotlight.centerScreen.y, window.innerHeight - spotlight.centerScreen.y);
    const maxRadius = Math.hypot(maxDx, maxDy) * 0.5;
    setHoleRadius(maxRadius);

    const animate = (
      fromOpacity: number,
      toOpacity: number,
      fromRadius: number,
      toRadius: number,
      durationMs: number,
      onDone: () => void,
    ) => {
      const startedAt = performance.now();
      const tick = (now: number) => {
        const elapsed = now - startedAt;
        const linear = durationMs <= 0 ? 1 : Math.min(1, elapsed / durationMs);
        const eased = easeInOutCubic(linear);
        setOpacity(fromOpacity + (toOpacity - fromOpacity) * eased);
        setHoleRadius(fromRadius + (toRadius - fromRadius) * eased);
        if (linear < 1) {
          rafRef.current = window.requestAnimationFrame(tick);
          return;
        }
        rafRef.current = null;
        onDone();
      };
      rafRef.current = window.requestAnimationFrame(tick);
    };

    const startExit = () => {
      animate(1, 0, spotlight.radius, maxRadius, spotlight.exitMs, () => {
        const latest = useAppStore.getState().focusSpotlight;
        if (!latest) {
          return;
        }
        if (latest.id !== spotlight.id) {
          return;
        }
        clearFocusSpotlight();
      });
    };

    animate(0, 1, maxRadius, spotlight.radius, spotlight.enterMs, () => {
      const holdTimer = window.setTimeout(startExit, spotlight.holdMs);
      timersRef.current.push(holdTimer);
    });

    return () => {
      if (rafRef.current !== null) {
        window.cancelAnimationFrame(rafRef.current);
        rafRef.current = null;
      }
      for (const timer of timersRef.current) {
        window.clearTimeout(timer);
      }
      timersRef.current = [];
    };
  }, [clearFocusSpotlight, spotlight]);

  const active = useMemo(() => {
    if (!spotlight || renderedId !== spotlight.id) {
      return null;
    }
    return spotlight;
  }, [renderedId, spotlight]);

  if (!active) {
    return null;
  }

  const maskId = `kb-focus-spotlight-mask-${active.id}`;

  return (
    <div
      style={{
        position: "fixed",
        inset: 0,
        zIndex: 2000,
        pointerEvents: "auto",
      }}
    >
      <svg width="100%" height="100%" style={{ display: "block" }}>
        <defs>
          <mask id={maskId}>
            <rect x="0" y="0" width="100%" height="100%" fill="white" />
            <circle cx={active.centerScreen.x} cy={active.centerScreen.y} r={Math.max(8, holeRadius)} fill="black" />
          </mask>
        </defs>
        <rect
          x="0"
          y="0"
          width="100%"
          height="100%"
          fill="rgba(15, 23, 42, 0.66)"
          mask={`url(#${maskId})`}
          style={{ opacity }}
        />
      </svg>
    </div>
  );
};
