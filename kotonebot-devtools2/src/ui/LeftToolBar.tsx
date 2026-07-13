import React, { useCallback, useMemo } from "react";
import { IconName } from "@blueprintjs/core";
import { useTranslation } from "react-i18next";
import { useAppStore } from "../editor/state";
import { SideToolBar, Tool } from "./SideToolBar";
import { toaster } from "./toaster";
import { useShortcuts } from "../shortcuts/shortcutManager";

export const LeftToolBar: React.FC = () => {
  const { t } = useTranslation();
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
          tool: primaryPropSchema.kind as "rect" | "point" | "image",
        });
        return;
      }
    }

    toaster.show({ message: t('error.noPrimaryProp', { name: schema.name }), intent: "danger" });
  }, [activeMeta, prefabSchema, setMode]);

  const prefabShortcutBindings = useMemo(() => {
    if (!prefabSchema) {
      return [];
    }
    return Object.values(prefabSchema.prefabs)
      .filter((prefab) => !!prefab.shortcut)
      .map((prefab) => ({
        id: `editor.prefab.${prefab.id}`,
        scope: "editor",
        combo: prefab.shortcut!.replace(/^ctrl\+/i, "mod+"),
        when: () => !!prefabSchema,
        onKeyDown: () => createPrefab(prefab.id),
      }));
  }, [createPrefab, prefabSchema]);

  useShortcuts([
    {
      id: "editor.redo",
      scope: "editor",
      combo: "mod+shift+z",
      when: () => canRedo,
      onKeyDown: () => redo(),
    },
    {
      id: "editor.undo",
      scope: "editor",
      combo: "mod+z",
      when: () => canUndo,
      onKeyDown: () => undo(),
    },
    {
      id: "editor.select-tool",
      scope: "editor",
      combo: "v",
      onKeyDown: () => setActiveTool("select"),
    },
    ...prefabShortcutBindings,
  ]);

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
      title: t('toolbar.select'),
      selectable: true,
      onClick: () => setActiveTool("select"),
    },
    "separator",
  ];

  let hasPrefabTools = false;
  if (prefabSchema) {
    Object.values(prefabSchema.prefabs).forEach((p) => {
      const shortcut = p.shortcut || 'no shortcut';
      tools.push({
        id: `prefab-${p.id}`,
        icon: p.icon as IconName,
        title: `${p.name} (${shortcut})`,
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
    title: t('toolbar.template'),
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
    title: t('toolbar.hintBox'),
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
    title: t('toolbar.hintPoint'),
    selectable: true,
    onClick: () => {
      setActiveResourceType("hint-point");
      setActiveTool("point");
    },
    disabled: !activeMeta,
  });

  return <SideToolBar tools={tools} selectedToolId={getSelectedToolId()} />;
};
