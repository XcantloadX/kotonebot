import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { IconName, InputGroup, Menu, MenuItem } from "@blueprintjs/core";
import { editorActions } from "../editor/actions";
import { useAppStore } from "../editor/state";
import { FileOpenDialog } from "./components/FileOpenDialog/FileOpenDialog";
import { FileOpenOrImportDialog } from "./components/FileOpenDialog/FileOpenOrImportDialog";
import { useShortcut, useShortcutScope } from "../shortcuts/shortcutManager";

interface TopMenuBarProps {
  onOpenCommandPalette: () => void;
}

type MenuKey = "file" | "edit" | "variant" | null;
type MenuId = Exclude<MenuKey, null>;

interface MenuDefinitionItem {
  icon: IconName;
  text: string;
  label?: string;
  disabled?: boolean;
  onClick: () => void;
}

export const TopMenuBar: React.FC<TopMenuBarProps> = ({
  onOpenCommandPalette,
}) => {
  const { undo, redo, activeDocumentId, documents } = useAppStore();
  const activeDoc = activeDocumentId ? documents[activeDocumentId] : null;
  const activeMeta = activeDoc?.meta;
  const canSave = !!activeMeta;
  const canSaveAll = Object.values(documents).some((doc) => doc.dirty);
  const canRenameDocument = !!activeMeta;
  const canCreateVariantDocument = !!activeMeta;
  const canCopySelectedPrefabToVariant = !!activeMeta
    && !!activeDoc?.selection
    && activeMeta.data.definitions[activeDoc.selection.definitionId]?.type === "prefab";
  const canUndo = !!activeDoc && activeDoc.history.cursor > 0;
  const canRedo = !!activeDoc && activeDoc.history.cursor < activeDoc.history.entries.length;
  const undoLabel = canUndo ? activeDoc.history.entries[activeDoc.history.cursor - 1].label : "";
  const redoLabel = canRedo ? activeDoc.history.entries[activeDoc.history.cursor].label : "";
  const undoMenuText = canUndo ? `Undo: ${undoLabel}` : "Undo";
  const redoMenuText = canRedo ? `Redo: ${redoLabel}` : "Redo";
  const fileButtonRef = useRef<HTMLButtonElement>(null);
  const editButtonRef = useRef<HTMLButtonElement>(null);
  const variantButtonRef = useRef<HTMLButtonElement>(null);
  const menuPanelRef = useRef<HTMLDivElement>(null);
  const [openMenu, setOpenMenu] = useState<MenuKey>(null);
  const [menuPosition, setMenuPosition] = useState({ left: 0, top: 0 });
  const [isImageDialogOpen, setImageDialogOpen] = useState(false);
  const [projectVariants, setProjectVariants] = useState<string[]>([]);
  const [variantDialogState, setVariantDialogState] = useState<{ isOpen: boolean; variant: string | null }>({
    isOpen: false,
    variant: null,
  });
  const variantDialogTitle = variantDialogState.variant
    ? `Select target image for variant ${variantDialogState.variant}`
    : "Select target image for variant";
  const hasAnyDocument = Object.keys(documents).length > 0;
  const modalOpen = isImageDialogOpen || variantDialogState.isOpen;

  useShortcutScope("menu", openMenu !== null);
  useShortcutScope("modal", modalOpen);

  useEffect(() => {
    (async () => {
      try {
        setProjectVariants(await editorActions.variant.loadOptions());
      } catch {
        setProjectVariants([]);
      }
    })();
  }, []);

  const openImageDialog = useCallback(() => {
    setImageDialogOpen(true);
  }, []);

  const closeImageDialog = useCallback(() => {
    setImageDialogOpen(false);
  }, []);

  const closeVariantDialog = useCallback(() => {
    setVariantDialogState({ isOpen: false, variant: null });
  }, []);

  const openVariantDialog = useCallback(async () => {
    const variant = await editorActions.variant.pickForActive(projectVariants);
    if (variant === null) {
      return;
    }
    setVariantDialogState({ isOpen: true, variant });
  }, [projectVariants]);

  const handleCopySelectedPrefabToVariant = useCallback(async () => {
    const variant = await editorActions.variant.pickForActive(projectVariants);
    if (variant === null) {
      return;
    }
    await editorActions.variant.copySelectedPrefabForActive(variant);
  }, [projectVariants]);

  const handleSelectImages = useCallback(
    async (paths: string[]) => {
      await editorActions.image.openWithChecks(paths);
      setImageDialogOpen(false);
    },
    []
  );

  const handleSelectVariantImage = useCallback(
    async (paths: string[]) => {
      const variant = variantDialogState.variant;
      if (!variant) {
        throw new Error("No variant selected for target image");
      }
      await editorActions.variant.selectImageForActive(paths, variant);
      setVariantDialogState({ isOpen: false, variant: null });
    },
    [variantDialogState.variant]
  );

  const handleImportVariantImage = useCallback(
    async (files: File[]) => {
      const variant = variantDialogState.variant;
      if (!variant) {
        throw new Error("No variant selected for import");
      }
      const shouldClose = await editorActions.variant.importImageForActive(files, variant);
      if (shouldClose) {
        setVariantDialogState({ isOpen: false, variant: null });
      }
      return shouldClose;
    },
    [variantDialogState.variant]
  );

  const triggerStyle = useMemo<React.CSSProperties>(
    () => ({
      height: 24,
      padding: "0 10px",
      border: "none",
      borderRadius: 3,
      background: "transparent",
      color: "#182026",
      fontSize: 14,
      lineHeight: "24px",
      cursor: "default",
      fontFamily: "inherit",
      display: "inline-flex",
      alignItems: "center",
    }),
    []
  );
  const menuDefinitions = useMemo<Record<MenuId, MenuDefinitionItem[]>>(
    () => ({
      file: [
        {
          icon: "folder-open",
          text: "Open Image...",
          label: "Ctrl+O",
          onClick: () => {
            setOpenMenu(null);
            openImageDialog();
          },
        },
        {
          icon: "floppy-disk",
          text: "Save",
          label: "Ctrl+S",
          disabled: !canSave,
          onClick: () => {
            setOpenMenu(null);
            void editorActions.document.save();
          },
        },
        {
          icon: "floppy-disk",
          text: "Save All",
          label: "Ctrl+Shift+S",
          disabled: !canSaveAll,
          onClick: () => {
            setOpenMenu(null);
            void editorActions.document.saveAll();
          },
        },
        {
          icon: "edit",
          text: "Rename...",
          disabled: !canRenameDocument,
          onClick: () => {
            setOpenMenu(null);
            void editorActions.document.renameByPrompt();
          },
        },
        {
          icon: "cross",
          text: "Close Document",
          label: "Ctrl+2",
          disabled: !activeDocumentId,
          onClick: () => {
            if (!activeDocumentId) {
              return;
            }
            setOpenMenu(null);
            void editorActions.document.closeActive();
          },
        },
        {
          icon: "small-cross",
          text: "Close All Document",
          label: "Ctrl+Shift+2",
          disabled: Object.keys(documents).length === 0,
          onClick: () => {
            setOpenMenu(null);
            void editorActions.document.closeAll();
          },
        },
      ],
      edit: [
        {
          icon: "undo",
          text: undoMenuText,
          label: "Ctrl+Z",
          disabled: !canUndo,
          onClick: () => {
            setOpenMenu(null);
            undo();
          },
        },
        {
          icon: "redo",
          text: redoMenuText,
          label: "Ctrl+Shift+Z",
          disabled: !canRedo,
          onClick: () => {
            setOpenMenu(null);
            redo();
          },
        },
      ],
      variant: [
        {
          icon: "duplicate",
          text: "New Variant Image Document...",
          label: "Ctrl+Alt+N",
          disabled: !canCreateVariantDocument,
          onClick: () => {
            setOpenMenu(null);
            void openVariantDialog();
          },
        },
        {
          icon: "duplicate",
          text: "Copy Selected Prefab to Variant",
          disabled: !canCopySelectedPrefabToVariant,
          onClick: () => {
            setOpenMenu(null);
            void handleCopySelectedPrefabToVariant();
          },
        },
      ],
    }),
    [
      activeDocumentId,
      canCopySelectedPrefabToVariant,
      canCreateVariantDocument,
      canRedo,
      canRenameDocument,
      canSave,
      canSaveAll,
      canUndo,
      documents,
      handleCopySelectedPrefabToVariant,
      openImageDialog,
      openVariantDialog,
      redoMenuText,
      redo,
      undoMenuText,
      undo,
    ]
  );

  const getMenuButton = useCallback((key: MenuId) => {
    if (key === "file") {
      return fileButtonRef.current;
    }
    if (key === "edit") {
      return editButtonRef.current;
    }
    return variantButtonRef.current;
  }, []);

  const openMenuAt = useCallback(
    (key: MenuId) => {
      const target = getMenuButton(key);
      if (!target) {
        throw new Error(`Menu button for key '${key}' is not mounted`);
      }
      const rect = target.getBoundingClientRect();
      setMenuPosition({
        left: Math.round(rect.left),
        top: Math.round(rect.bottom),
      });
      setOpenMenu(key);
    },
    [getMenuButton]
  );

  const toggleMenu = (key: MenuId) => {
    setOpenMenu((prev) => {
      if (prev === key) {
        return null;
      }
      return prev;
    });
    if (openMenu !== key) {
      openMenuAt(key);
    }
  };

  const switchMenuOnHover = (key: MenuId) => {
    if (openMenu) {
      openMenuAt(key);
    }
  };

  useEffect(() => {
    if (!openMenu) {
      return;
    }
    const updatePosition = () => {
      const target = getMenuButton(openMenu);
      if (!target) {
        throw new Error(`Menu button for key '${openMenu}' is not mounted`);
      }
      const rect = target.getBoundingClientRect();
      setMenuPosition({
        left: Math.round(rect.left),
        top: Math.round(rect.bottom),
      });
    };
    updatePosition();
    window.addEventListener("resize", updatePosition);
    window.addEventListener("scroll", updatePosition, true);
    return () => {
      window.removeEventListener("resize", updatePosition);
      window.removeEventListener("scroll", updatePosition, true);
    };
  }, [getMenuButton, openMenu]);

  useEffect(() => {
    if (!openMenu) {
      return;
    }
    const closeIfOutside = (e: MouseEvent) => {
      const target = e.target as Node;
      const isInPanel = menuPanelRef.current?.contains(target) ?? false;
      const isOnFileButton = fileButtonRef.current?.contains(target) ?? false;
      const isOnEditButton = editButtonRef.current?.contains(target) ?? false;
      const isOnVariantButton = variantButtonRef.current?.contains(target) ?? false;
      if (!isInPanel && !isOnFileButton && !isOnEditButton && !isOnVariantButton) {
        setOpenMenu(null);
      }
    };
    window.addEventListener("mousedown", closeIfOutside);
    return () => {
      window.removeEventListener("mousedown", closeIfOutside);
    };
  }, [openMenu]);

  useShortcut({
    id: "menu.close-by-escape",
    scope: "menu",
    combo: "escape",
    onKeyDown: () => setOpenMenu(null),
  });

  useShortcut({
    id: "editor.open-image",
    scope: "editor",
    combo: "mod+o",
    onKeyDown: () => openImageDialog(),
  });

  useShortcut({
    id: "editor.save-document",
    scope: "editor",
    combo: "mod+s",
    when: () => canSave,
    onKeyDown: () => {
      void editorActions.document.save();
    },
  });

  useShortcut({
    id: "editor.save-all-documents",
    scope: "editor",
    combo: "mod+shift+s",
    when: () => canSaveAll,
    onKeyDown: () => {
      void editorActions.document.saveAll();
    },
  });

  useShortcut({
    id: "editor.close-active-document",
    scope: "editor",
    combo: "mod+2",
    when: () => !!activeDocumentId,
    onKeyDown: () => {
      void editorActions.document.closeActive();
    },
  });

  useShortcut({
    id: "editor.close-all-document",
    scope: "editor",
    combo: "mod+shift+2",
    when: () => hasAnyDocument,
    onKeyDown: () => {
      void editorActions.document.closeAll();
    },
  });

  useShortcut({
    id: "editor.open-variant-dialog",
    scope: "editor",
    combo: "mod+alt+n",
    when: () => canCreateVariantDocument,
    onKeyDown: () => {
      void openVariantDialog();
    },
  });

  const renderMenu = () => {
    if (!openMenu) {
      return null;
    }
    return (
      <Menu>
        {menuDefinitions[openMenu].map((item) => (
          <MenuItem
            key={`${openMenu}-${item.text}`}
            icon={item.icon}
            text={item.text}
            label={item.label}
            disabled={item.disabled}
            onClick={item.onClick}
          />
        ))}
      </Menu>
    );
  };

  return (
    <div
      style={{
        height: 34,
        display: "grid",
        gridTemplateColumns: "1fr minmax(260px, 520px) 1fr",
        alignItems: "center",
        gap: 10,
        padding: "0 8px",
        background: "#dde5ec",
        borderBottom: "1px solid #b8c6d2",
        flex: "0 0 auto",
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: 4 }}>
        <button
          ref={fileButtonRef}
          type="button"
          style={{ ...triggerStyle, background: openMenu === "file" ? "#c7d4e0" : "transparent" }}
          onClick={() => toggleMenu("file")}
          onMouseEnter={() => switchMenuOnHover("file")}
        >
          File
        </button>
        <button
          ref={editButtonRef}
          type="button"
          style={{ ...triggerStyle, background: openMenu === "edit" ? "#c7d4e0" : "transparent" }}
          onClick={() => toggleMenu("edit")}
          onMouseEnter={() => switchMenuOnHover("edit")}
        >
          Edit
        </button>
        <button
          ref={variantButtonRef}
          type="button"
          style={{ ...triggerStyle, background: openMenu === "variant" ? "#c7d4e0" : "transparent" }}
          onClick={() => toggleMenu("variant")}
          onMouseEnter={() => switchMenuOnHover("variant")}
        >
          Variant
        </button>
      </div>
      <div
        onMouseDown={(e) => {
          e.preventDefault();
          onOpenCommandPalette();
        }}
      >
        <InputGroup
          leftIcon="search"
          value=""
          readOnly
          placeholder="Search commands and symbols"
          rightElement={<div style={{ padding: "6px 10px", color: "#5c7080", fontSize: 12 }}>Ctrl+Shift+P</div>}
        />
      </div>
      <div />
      {openMenu ? (
        <div
          ref={menuPanelRef}
          style={{
            position: "fixed",
            left: menuPosition.left,
            top: menuPosition.top,
            zIndex: 2500,
            minWidth: 220,
            background: "#ffffff",
            border: "1px solid #b7c6d2",
            borderRadius: 3,
            boxShadow: "0 6px 18px rgba(16, 22, 26, 0.22)",
          }}
          onMouseDown={(e) => e.stopPropagation()}
        >
          {renderMenu()}
        </div>
      ) : null}
      <FileOpenDialog
        isOpen={isImageDialogOpen}
        onClose={closeImageDialog}
        onSelect={handleSelectImages}
        title="Open Image"
        filter={(name) => name.endsWith(".png")}
      />
      <FileOpenOrImportDialog
        isOpen={variantDialogState.isOpen}
        onClose={closeVariantDialog}
        onSelect={handleSelectVariantImage}
        onImportDrop={handleImportVariantImage}
        title={variantDialogTitle}
        filter={(name) => name.endsWith(".png")}
        multiSelect={false}
      />
    </div>
  );
};
