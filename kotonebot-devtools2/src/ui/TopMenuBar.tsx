import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { IconName, InputGroup, Menu, MenuItem } from "@blueprintjs/core";
import { useEditorCommands } from "../editor/useEditorCommands";
import { useAppStore } from "../editor/state";
import { FileOpenDialog } from "./FileOpenDialog";

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
  const {
    canSave,
    canCreateVariantDocument,
    isImageDialogOpen,
    isVariantImageDialogOpen,
    variantDialogTitle,
    openImageDialog,
    closeImageDialog,
    selectImages,
    saveDocument,
    createVariantDocument,
    closeVariantDialog,
    selectVariantImage,
  } = useEditorCommands();
  const { undo, redo } = useAppStore();
  const fileButtonRef = useRef<HTMLButtonElement>(null);
  const editButtonRef = useRef<HTMLButtonElement>(null);
  const variantButtonRef = useRef<HTMLButtonElement>(null);
  const menuPanelRef = useRef<HTMLDivElement>(null);
  const [openMenu, setOpenMenu] = useState<MenuKey>(null);
  const [menuPosition, setMenuPosition] = useState({ left: 0, top: 0 });
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
            void saveDocument();
          },
        },
      ],
      edit: [
        {
          icon: "undo",
          text: "Undo",
          label: "Ctrl+Z",
          onClick: () => {
            setOpenMenu(null);
            undo();
          },
        },
        {
          icon: "redo",
          text: "Redo",
          label: "Ctrl+Shift+Z",
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
          disabled: !canCreateVariantDocument,
          onClick: () => {
            setOpenMenu(null);
            createVariantDocument();
          },
        },
      ],
    }),
    [canCreateVariantDocument, canSave, createVariantDocument, openImageDialog, redo, saveDocument, undo]
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
    const closeByEscape = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        setOpenMenu(null);
      }
    };
    window.addEventListener("mousedown", closeIfOutside);
    window.addEventListener("keydown", closeByEscape);
    return () => {
      window.removeEventListener("mousedown", closeIfOutside);
      window.removeEventListener("keydown", closeByEscape);
    };
  }, [openMenu]);

  useEffect(() => {
    const onKeyDown = (e: KeyboardEvent) => {
      const target = e.target as HTMLElement | null;
      const isTyping =
        target instanceof HTMLInputElement ||
        target instanceof HTMLTextAreaElement ||
        target?.isContentEditable;
      if (isTyping) {
        return;
      }

      const key = e.key.toLowerCase();
      if (e.ctrlKey && key === "o") {
        e.preventDefault();
        openImageDialog();
      } else if (e.ctrlKey && key === "s") {
        if (!canSave) {
          return;
        }
        e.preventDefault();
        void saveDocument();
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [canSave, openImageDialog, saveDocument]);

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
        onSelect={selectImages}
        title="Open Image"
        filter={(name) => name.endsWith(".png")}
      />
      <FileOpenDialog
        isOpen={isVariantImageDialogOpen}
        onClose={closeVariantDialog}
        onSelect={selectVariantImage}
        title={variantDialogTitle}
        filter={(name) => name.endsWith(".png")}
        multiSelect={false}
      />
    </div>
  );
};
