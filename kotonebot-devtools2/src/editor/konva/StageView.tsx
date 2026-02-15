import React, { useRef, useState, useMemo, useEffect } from 'react';
import { Stage, Layer, Image as KonvaImage, Rect, Circle, Line } from 'react-konva';
import useImage from 'use-image';
import { useAppStore } from '../state';
import { useSymbolIndexStore } from '../symbolIndexStore';
import { readText } from '../../api/fs';
import { DefinitionV2 } from '../../model/metaV2';
import { toaster } from '../../ui/toaster';
import { KonvaEventObject } from 'konva/lib/Node';
import { ToolContext } from '../tools/Tool';
import { SelectTool } from '../tools/SelectTool';
import { RectTool } from '../tools/RectTool';
import { PointTool } from '../tools/PointTool';
import { PickingTool } from '../tools/PickingTool';
import { CreatingPrefabTool } from '../tools/CreatingPrefabTool';
import { DefinitionRect } from './shapes/DefinitionRect';
import { DefinitionPoint } from './shapes/DefinitionPoint';
import { useShortcuts } from '../../hooks/useShortcut';

export const StageView: React.FC = () => {
  const {
    activeDocumentId,
    documents,
    activeTool,
    activeResourceType,
    setSelection,
    updateMeta,
    setMode,
    prefabSchema,
    setViewState
  } = useAppStore();
  const symbols = useSymbolIndexStore(s => s.symbols);

  const activeDoc = activeDocumentId ? documents[activeDocumentId] : null;
  const activeImage = activeDoc?.image;
  const activeMeta = activeDoc?.meta;
  const selection = activeDoc?.selection || null;
  const mode = activeDoc?.mode || { kind: "idle" };
  const view = activeDoc?.view;

  const [image] = useImage(activeImage?.url || '', 'anonymous');

  // Container size
  const containerRef = useRef<HTMLDivElement>(null);
  const [size, setSize] = useState({ width: 0, height: 0 });

  // stage 缩放比例
  const scale = view?.scale || 1;
  // stage 位置
  const position = { x: view?.x || 0, y: view?.y || 0 };

  // 当前正在绘制的 shape
  const [preview, setPreview] = useState<any>(null);
  // Cursor position for crosshair
  const [cursorPos, setCursorPos] = useState<{ x: number, y: number } | null>(null);
  // Space key state for panning
  const [isSpacePressed, setIsSpacePressed] = useState(false);
  // Panning state
  const [isPanning, setIsPanning] = useState(false);
  // panOrigin holds the view position and pointer position at the start of a pan
  const [panOrigin, setPanOrigin] = useState<{ viewX: number, viewY: number, pointerX: number, pointerY: number } | null>(null);
  // right mouse button state for panning
  const [isRightMouseDown, setIsRightMouseDown] = useState(false);
  const [baseDefinitionsByName, setBaseDefinitionsByName] = useState<Record<string, DefinitionV2>>({});
  const [baseDefsReady, setBaseDefsReady] = useState(true);
  const missingBaseToastKeyRef = useRef<string>("");

  const stageRef = useRef<any>(null);

  useEffect(() => {
    let cancelled = false;
    const loadBaseDefinitions = async () => {
      if (!activeMeta) {
        setBaseDefinitionsByName({});
        setBaseDefsReady(true);
        return;
      }
      const variantDefs = Object.values(activeMeta.data.definitions).filter(
        (def) => def.type === "prefab" && !!def.variant && !!def.name,
      );
      if (variantDefs.length === 0) {
        setBaseDefinitionsByName({});
        setBaseDefsReady(true);
        return;
      }

      const byName: Record<string, DefinitionV2> = {};
      const loadedMetaCache: Record<string, any> = {};
      const missingNames: string[] = [];
      for (const def of variantDefs) {
        const name = def.name as string;
        const baseSymbol = symbols.find((s) => s.type === "prefab" && s.name === name && s.variant === null);
        if (!baseSymbol) {
          missingNames.push(name);
          continue;
        }
        if (!loadedMetaCache[baseSymbol.metaPath]) {
          const text = await readText(baseSymbol.metaPath);
          loadedMetaCache[baseSymbol.metaPath] = JSON.parse(text);
        }
        const baseMeta = loadedMetaCache[baseSymbol.metaPath];
        if (!baseMeta || baseMeta.version !== 2 || !baseMeta.definitions) {
          missingNames.push(name);
          continue;
        }
        const baseDef = baseMeta.definitions[baseSymbol.definitionId];
        if (!baseDef || baseDef.type !== "prefab") {
          missingNames.push(name);
          continue;
        }
        byName[name] = baseDef as DefinitionV2;
      }
      if (!cancelled) {
        setBaseDefinitionsByName(byName);
        setBaseDefsReady(true);
        if (missingNames.length > 0) {
          const key = missingNames.sort().join("|");
          if (missingBaseToastKeyRef.current !== key) {
            missingBaseToastKeyRef.current = key;
            toaster.show({
              message: `Missing base prefab definitions: ${missingNames.slice(0, 3).join(", ")}${missingNames.length > 3 ? " ..." : ""}`,
              intent: "warning",
            });
          }
        } else {
          missingBaseToastKeyRef.current = "";
        }
      }
    };
    setBaseDefsReady(false);
    void loadBaseDefinitions().catch((err) => {
      if (cancelled) return;
      setBaseDefinitionsByName({});
      setBaseDefsReady(true);
      toaster.show({ message: err instanceof Error ? err.message : String(err), intent: "danger" });
    });
    return () => {
      cancelled = true;
    };
  }, [activeMeta, symbols]);

  const renderDefinitions = useMemo(() => {
    if (!activeMeta) return null;
    const out: Record<string, DefinitionV2> = {};
    for (const [defId, def] of Object.entries(activeMeta.data.definitions)) {
      if (def.type === "prefab" && def.variant && def.name) {
        const baseDef = baseDefinitionsByName[def.name];
        if (!baseDef) {
          if (baseDefsReady) {
            out[defId] = def;
          }
          continue;
        }
        out[defId] = {
          ...baseDef,
          ...def,
          props: {
            ...(baseDef.props || {}),
            ...(def.props || {}),
          },
        };
      } else {
        out[defId] = def;
      }
    }
    return out;
  }, [activeMeta, baseDefinitionsByName, baseDefsReady]);

  useEffect(() => {
    if (!containerRef.current) return;
    const observer = new ResizeObserver(entries => {
      for (const entry of entries) {
        setSize({
          width: entry.contentRect.width,
          height: entry.contentRect.height
        });
      }
    });
    observer.observe(containerRef.current);
    return () => observer.disconnect();
  }, []);

  useShortcuts({
    'Space': {
      onKeyDown: (e) => {
        if (!e.repeat) {
          setIsSpacePressed(true);
        }
      },
      onKeyUp: () => {
        setIsSpacePressed(false);
        setIsPanning(false);
        setPanOrigin(null);
      }
    },
    'Escape': {
      onKeyDown: () => {
        if (mode.kind === 'picking' || mode.kind === 'creating-prefab') {
          setMode({ kind: 'idle' });
          setPreview(null);
        }
      }
    }
  });

  useEffect(() => {
    if (!view && image && size.width > 0 && size.height > 0 && activeDocumentId) {
      const x = (size.width - image.width) / 2;
      const y = (size.height - image.height) / 2;
      setViewState(activeDocumentId, { x, y, scale: 1 });
    }
  }, [view, image, size.width, size.height, activeDocumentId, setViewState]);

  const tool = useMemo(() => {
    if (mode.kind === 'picking') {
      return new PickingTool(mode.definitionId, mode.propKey, mode.tool);
    }
    if (mode.kind === 'creating-prefab') {
      return new CreatingPrefabTool(mode.prefab_id, mode.propKey, mode.tool);
    }
    switch (activeTool) {
      case 'rect': return new RectTool();
      case 'point': return new PointTool();
      case 'select': return new SelectTool();
      default: return new SelectTool();
    }
  }, [mode, activeTool]);

  const getToolContext = (): ToolContext => {
    const stage = stageRef.current;
    return {
      activeMeta: activeMeta ?? null,
      prefabSchema,
      activeResourceType,
      updateMeta,
      setSelection,
      setMode,
      scale,
      position,
      setPosition: (pos) => {
        if (activeDocumentId) {
          setViewState(activeDocumentId, { x: pos.x, y: pos.y, scale });
        }
      },
      getRelativePointerPosition: () => {
        if (!stage) return { x: 0, y: 0 };
        const transform = stage.getAbsoluteTransform().copy();
        transform.invert();
        const pos = stage.getPointerPosition();
        return transform.point(pos || { x: 0, y: 0 });
      }
    };
  };

  const handleMouseDown = (e: KonvaEventObject<MouseEvent>) => {
    // Right mouse button (button === 2) also starts panning
    if (e.evt.button === 2) {
      e.evt.preventDefault();
      setIsRightMouseDown(true);
      setIsPanning(true);
      setPanOrigin({ viewX: position.x, viewY: position.y, pointerX: e.evt.clientX, pointerY: e.evt.clientY });
      return;
    }

    if (isSpacePressed) {
      setIsPanning(true);
      setPanOrigin({ viewX: position.x, viewY: position.y, pointerX: e.evt.clientX, pointerY: e.evt.clientY });
      return;
    }
    const stage = stageRef.current;
    // click on empty stage (or background image) should clear selection
    if (mode.kind === 'idle' && activeTool === 'select' && stage) {
      const pointer = stage.getPointerPosition();
      const hit = pointer ? stage.getIntersection(pointer) : null;
      const cls = hit ? hit.getClassName() : null;
      if (!hit || cls === 'Image' || cls === 'Stage' || cls === 'Layer') {
        setSelection(null);
        return;
      }
    }

    tool.onMouseDown(e, getToolContext());
    setPreview(tool.getPreview());
  };

  const handleMouseMove = (e: KonvaEventObject<MouseEvent>) => {
    if (isPanning && panOrigin && activeDocumentId) {
      const dx = e.evt.clientX - panOrigin.pointerX;
      const dy = e.evt.clientY - panOrigin.pointerY;
      setViewState(activeDocumentId, { x: panOrigin.viewX + dx, y: panOrigin.viewY + dy, scale });
      return;
    }

    tool.onMouseMove(e, getToolContext());
    setPreview(tool.getPreview());

    // 记录光标坐标，用于绘制十字线
    const stage = stageRef.current;
    if (stage) {
      const transform = stage.getAbsoluteTransform().copy();
      transform.invert();
      const pos = stage.getPointerPosition();
      if (pos) {
        setCursorPos(transform.point(pos));
      }
    }
  };

  const handleMouseUp = (e: KonvaEventObject<MouseEvent>) => {
    // If right button was used for panning, clear that state
    if (isRightMouseDown && e.evt.button === 2) {
      setIsRightMouseDown(false);
      setIsPanning(false);
      setPanOrigin(null);
      return;
    }

    if (isPanning) {
      setIsPanning(false);
      setPanOrigin(null);
      return;
    }
    tool.onMouseUp(e, getToolContext());
    setPreview(tool.getPreview());
  };

  const handleShapeClick = (id: string, e: KonvaEventObject<MouseEvent>) => {
    if (isSpacePressed || isRightMouseDown) return;
    tool.onShapeClick(id, e, getToolContext());
  };

  const handleWheel = (e: KonvaEventObject<WheelEvent>) => {
    e.evt.preventDefault();
    if (!activeDocumentId) return;
    const stage = stageRef.current;
    // Ctrl + Wheel: Zoom
    if (e.evt.ctrlKey) {
      const oldScale = stage.scaleX();
      const pointer = stage.getPointerPosition();
      if (!pointer) return;

      const scaleBy = 1.1;
      const newScale = e.evt.deltaY < 0 ? oldScale * scaleBy : oldScale / scaleBy;

      const mousePointTo = {
        x: (pointer.x - stage.x()) / oldScale,
        y: (pointer.y - stage.y()) / oldScale,
      };

      const newPos = {
        x: pointer.x - mousePointTo.x * newScale,
        y: pointer.y - mousePointTo.y * newScale,
      };

      setViewState(activeDocumentId, { x: newPos.x, y: newPos.y, scale: newScale });
      return;
    }

    // Shift + Wheel: Horizontal Scroll
    if (e.evt.shiftKey) {
      setViewState(activeDocumentId, { x: position.x - e.evt.deltaY, y: position.y, scale });
      return;
    }

    // Default (plain wheel): Vertical Scroll
    setViewState(activeDocumentId, { x: position.x, y: position.y - e.evt.deltaY, scale });
  };

  if (!activeImage) return null;

  const showCrosshair = !isSpacePressed && !isRightMouseDown && cursorPos && (activeTool === 'rect' || activeTool === 'point' || mode.kind === 'picking' || mode.kind === 'creating-prefab');
  const cursor = isPanning ? 'grabbing' : (isSpacePressed || isRightMouseDown) ? 'grab' : tool.getCursor();

  return (
    <div ref={containerRef} style={{ width: '100%', height: '100%', overflow: 'hidden', background: '#e1e8ed' }}>
      {size.width > 0 && size.height > 0 && (
        <Stage
          width={size.width}
          height={size.height}
          onMouseDown={handleMouseDown}
          onMouseMove={handleMouseMove}
          onMouseUp={handleMouseUp}
          onContextMenu={(e) => e.evt.preventDefault()}
          onWheel={handleWheel}
          scaleX={scale}
          scaleY={scale}
          x={position.x}
          y={position.y}
          ref={stageRef}
          style={{ cursor }}
        >
          <Layer>
            {image && <KonvaImage image={image} name="bgImage" />}

            {renderDefinitions && Object.entries(renderDefinitions).map(([id, def]) => (
              <React.Fragment key={id}>
                {Object.entries(def.props).map(([key, val]: [string, any]) => {
                  if (!val) return null;
                  const isSelected = selection?.definitionId === id;

                  // Only render primary prop by default; non-primary props render only when the definition is selected
                  const prefab = def.prefab_id && prefabSchema ? prefabSchema.prefabs[def.prefab_id] : undefined;
                  const primaryProp = prefab?.primary_prop;
                  if (primaryProp && key !== primaryProp && !isSelected) return null;

                  // If currently picking this property's geometry, hide the existing shape
                  const isBeingPicked = mode.kind === 'picking' && mode.definitionId === id && mode.propKey === key;
                  if (isBeingPicked) return null;

                  if (val.kind === 'rect' || val.kind === 'image') {
                    return (
                      <DefinitionRect
                        key={`${id}-${key}`}
                        id={id}
                        propKey={key}
                        x1={val.x1} y1={val.y1} x2={val.x2} y2={val.y2}
                        kind={val.kind}
                        label={`${def.displayName || def.name} (${def.prefab_id || val.kind})`}
                        isSelected={isSelected}
                        scale={scale}
                        onClick={handleShapeClick}
                        onResize={(defId, propKey, rect) => {
                          updateMeta(draft => {
                            const d = draft.definitions[defId];
                            if (!d) return;
                            if (!d.props) d.props = {} as any;
                            const p = d.props[propKey || ''];
                            d.props[propKey || ''] = { kind: val.kind, ...(p as any || {}), ...(rect as any) };
                          });
                        }}
                      />
                    );
                  } else if (val.kind === 'point') {
                    return (
                      <DefinitionPoint
                        key={`${id}-${key}`}
                        id={id}
                        x={val.x} y={val.y}
                        isSelected={isSelected}
                        scale={scale}
                        onClick={handleShapeClick}
                      />
                    );
                  }
                  return null;
                })}
              </React.Fragment>
            ))}

            {preview && (
              preview.kind === 'point' ? (
                <Circle
                  x={preview.x}
                  y={preview.y}
                  radius={5 / scale}
                  fill="rgba(0, 255, 0, 0.5)"
                />
              ) : (
                <Rect
                  x={preview.x}
                  y={preview.y}
                  width={preview.width}
                  height={preview.height}
                  stroke="#48aff0"
                  strokeWidth={2 / scale}
                  dash={[5, 5]}
                />
              )
            )}
            {showCrosshair && (
              <>
                <Line
                  points={[-10000, cursorPos.y, 10000, cursorPos.y]}
                  stroke="red"
                  strokeWidth={1 / scale}
                  dash={[4, 4]}
                  listening={false}
                />
                <Line
                  points={[cursorPos.x, -10000, cursorPos.x, 10000]}
                  stroke="red"
                  strokeWidth={1 / scale}
                  dash={[4, 4]}
                  listening={false}
                />
              </>
            )}
          </Layer>
        </Stage>
      )}
    </div>
  );
};
