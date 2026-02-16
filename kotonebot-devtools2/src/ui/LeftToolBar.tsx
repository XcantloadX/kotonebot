import React, { useCallback, useEffect } from "react";
import { useAppStore } from "../editor/state";
import { SideToolBar, Tool } from "./SideToolBar";
import { toaster } from "./toaster";

export const LeftToolBar: React.FC = () => {
  const {
    activeDocumentId,
    documents,
    activeTool,
    setActiveTool,
    activeResourceType,
    setActiveResourceType,
    undo,
    redo,
    prefabSchema,
    setMode,
  } = useAppStore();

  const activeDoc = activeDocumentId ? documents[activeDocumentId] : null;
  const activeMeta = activeDoc?.meta;
  const activeMode = activeDoc?.mode;
  const canUndo = !!activeDoc && activeDoc.history.cursor > 0;
  const canRedo = !!activeDoc && activeDoc.history.cursor < activeDoc.history.entries.length;

  const createPrefab = useCallback((prefabId: string) => {
    if (!activeMeta || !prefabSchema) {
      return;
    }

    const schema = prefabSchema.prefabs[prefabId];
    if (schema.primary_prop) {
      const primaryPropSchema = schema.props[schema.primary_prop];
      if (primaryPropSchema) {
        setMode({
          kind: "creating-prefab",
          prefab_id: prefabId,
          propKey: schema.primary_prop,
          tool: primaryPropSchema.kind as any,
        });
        return;
      }
    }

    toaster.show({ message: `No primary prop defined for prefab '${schema.name}'`, intent: "danger" });
  }, [activeMeta, prefabSchema, setMode]);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) {
        return;
      }

      if (e.ctrlKey && e.shiftKey && (e.key === "z" || e.key === "Z")) {
        if (!canRedo) {
          return;
        }
        e.preventDefault();
        redo();
      } else if (e.ctrlKey && e.key === "z") {
        if (!canUndo) {
          return;
        }
        e.preventDefault();
        undo();
      } else if (e.key === "v") {
        setActiveTool("select");
      } else if (prefabSchema) {
        const key = e.key.toLowerCase();
        const isCtrl = e.ctrlKey;
        const target = Object.values(prefabSchema.prefabs).find((p) => {
          if (!p.shortcut) {
            return false;
          }
          const shortcut = p.shortcut.toLowerCase();
          if (shortcut.startsWith("ctrl+")) {
            return isCtrl && shortcut.slice(5) === key;
          }
          return !isCtrl && shortcut === key;
        });
        if (target) {
          e.preventDefault();
          createPrefab(target.id);
        }
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [canRedo, canUndo, createPrefab, prefabSchema, redo, setActiveTool, undo]);

  const getSelectedToolId = () => {
    if (activeMode && activeMode.kind === "creating-prefab") {
      return `prefab-${activeMode.prefab_id}`;
    }
    if (activeTool === "select") {
      return "select";
    }
    if (activeTool === "rect") {
      if (activeResourceType === "template") {
        return "new-template";
      }
      if (activeResourceType === "hint-box") {
        return "new-hint-box";
      }
    }
    if (activeTool === "point" && activeResourceType === "hint-point") {
      return "new-hint-point";
    }
    return undefined;
  };

  const tools: Array<Tool | "separator"> = [
    {
      id: "select",
      icon: "select",
      title: "选择",
      selectable: true,
      onClick: () => setActiveTool("select"),
    },
    "separator",
  ];

  let hasPrefabTools = false;
  if (prefabSchema) {
    Object.values(prefabSchema.prefabs).forEach((p) => {
      tools.push({
        id: `prefab-${p.id}`,
        icon: p.icon as any,
        title: `${p.name} (${p.shortcut || "no shortcut"})`,
        selectable: true,
        onClick: () => createPrefab(p.id),
        disabled: !activeMeta,
      });
      hasPrefabTools = true;
    });
  }

  if (hasPrefabTools) {
    tools.push("separator");
  }

  tools.push({
    id: "new-template",
    icon: "media",
    title: "简单模板",
    selectable: true,
    onClick: () => {
      setActiveResourceType("template");
      setActiveTool("rect");
    },
    disabled: !activeMeta,
  });
  tools.push({
    id: "new-hint-box",
    icon: "selection",
    title: "简单 Hint Box",
    selectable: true,
    onClick: () => {
      setActiveResourceType("hint-box");
      setActiveTool("rect");
    },
    disabled: !activeMeta,
  });
  tools.push({
    id: "new-hint-point",
    icon: "locate",
    title: "简单 Hint Point",
    selectable: true,
    onClick: () => {
      setActiveResourceType("hint-point");
      setActiveTool("point");
    },
    disabled: !activeMeta,
  });

  return <SideToolBar tools={tools} selectedToolId={getSelectedToolId()} />;
};
