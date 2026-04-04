import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { IconName, InputGroup, Menu, MenuItem, HTMLSelect, MenuDivider } from "@blueprintjs/core";
import { useTranslation } from "react-i18next";
import { editorActions } from "../editor/actions";
import { COMMAND_ID, executeCommand, useCommandStatuses } from "../editor/commands";
import { useAppStore } from "../editor/state";
import { FileOpenDialog } from "./components/FileOpenDialog/FileOpenDialog";
import { FileOpenOrImportDialog } from "./components/FileOpenDialog/FileOpenOrImportDialog";
import { DeviceCaptureDialog } from "./components/FileOpenDialog/DeviceCaptureDialog";
import { toaster } from "./toaster";
import { useShortcut, useShortcutScope } from "../shortcuts/shortcutManager";
import { useLocaleStore } from "../i18n/localeStore";
import { SUPPORTED_LANGUAGES } from "../i18n";
import { useRecentOpenStore } from "../editor/recentOpenStore";
import { shallow } from "zustand/shallow";

type MenuKey = "file" | "edit" | "variant" | null;
type MenuId = Exclude<MenuKey, null>;

interface MenuItemDefinition {
  icon?: IconName;
  text: string;
  label?: string;
  disabled?: boolean;
  children?: React.ReactNode;
  popoverProps?: { matchTargetWidth?: boolean };
  onClick?: () => void;
}

interface MenuDividerDefinition {
  divider: true;
}

type MenuDefinitionItem = MenuItemDefinition | MenuDividerDefinition;

export const TopMenuBar: React.FC = () => {
  const { t } = useTranslation();
  const { language, setLanguage } = useLocaleStore();
  const { activeDocumentId, documents } = useAppStore();
  const activeDoc = activeDocumentId ? documents[activeDocumentId] : null;
  const { clearRecentInWorkspace, currentWorkspaceKey, itemsByWorkspace } = useRecentOpenStore(
    (state) => ({
      clearRecentInWorkspace: state.clearCurrentWorkspace,
      currentWorkspaceKey: state.currentWorkspaceKey,
      itemsByWorkspace: state.itemsByWorkspace,
    }),
    shallow,
  );
  const recentItems = itemsByWorkspace[currentWorkspaceKey] ?? [];
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
  const [deviceCaptureState, setDeviceCaptureState] = useState<{ isOpen: boolean; variant: string | null }>({
    isOpen: false,
    variant: null,
  });
  const [rememberedVariant, setRememberedVariant] = useState<string | null>(null);
  const variantDialogTitle = variantDialogState.variant
    ? t('dialog.selectTargetImage') + ` ${variantDialogState.variant}`
    : t('dialog.selectTargetImage');
  const modalOpen = isImageDialogOpen || variantDialogState.isOpen || deviceCaptureState.isOpen;

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
    const variant = rememberedVariant ?? await editorActions.variant.pickForActive(projectVariants);
    if (variant === null) {
      return;
    }
    setVariantDialogState({ isOpen: true, variant });
  }, [projectVariants, rememberedVariant]);

  const commandContext = useMemo(
    () => ({
      ui: {
        openImageDialog,
        openVariantDialog,
      },
    }),
    [openImageDialog, openVariantDialog],
  );

  const statusEntries = useMemo(() => ([
    { id: COMMAND_ID.FILE_SAVE, args: undefined },
    { id: COMMAND_ID.FILE_SAVE_ALL, args: undefined },
    { id: COMMAND_ID.FILE_RENAME, args: undefined },
    { id: COMMAND_ID.FILE_CLOSE_ACTIVE, args: undefined },
    { id: COMMAND_ID.FILE_CLOSE_ALL, args: undefined },
    { id: COMMAND_ID.EDIT_UNDO, args: undefined },
    { id: COMMAND_ID.EDIT_REDO, args: undefined },
    { id: COMMAND_ID.VARIANT_NEW_DOCUMENT, args: undefined },
    { id: COMMAND_ID.VARIANT_COPY_SELECTED_PREFAB, args: undefined },
  ] as const), []);
  const statuses = useCommandStatuses(statusEntries, commandContext);
  const canSave = statuses[COMMAND_ID.FILE_SAVE].enabled;
  const canSaveAll = statuses[COMMAND_ID.FILE_SAVE_ALL].enabled;
  const canRenameDocument = statuses[COMMAND_ID.FILE_RENAME].enabled;
  const canCreateVariantDocument = statuses[COMMAND_ID.VARIANT_NEW_DOCUMENT].enabled;
  const canCopySelectedPrefabToVariant = statuses[COMMAND_ID.VARIANT_COPY_SELECTED_PREFAB].enabled;
  const canUndo = statuses[COMMAND_ID.EDIT_UNDO].enabled;
  const canRedo = statuses[COMMAND_ID.EDIT_REDO].enabled;
  const undoLabel = canUndo && activeDoc ? activeDoc.history.entries[activeDoc.history.cursor - 1].label : "";
  const redoLabel = canRedo && activeDoc ? activeDoc.history.entries[activeDoc.history.cursor].label : "";
  const undoMenuText = canUndo ? `${t('menuItem.undo')}: ${undoLabel}` : t('menuItem.undo');
  const redoMenuText = canRedo ? `${t('menuItem.redo')}: ${redoLabel}` : t('menuItem.redo');

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

  const handleDeviceCaptureImport = useCallback(
    async (files: File[]) => {
      const variant = deviceCaptureState.variant;
      if (!variant) {
        throw new Error("No variant selected for device capture");
      }
      const shouldClose = await editorActions.variant.importImageForActive(files, variant);
      if (shouldClose) {
        setDeviceCaptureState({ isOpen: false, variant: null });
      }
      return shouldClose;
    },
    [deviceCaptureState.variant]
  );

  const handleNewVariantFromClipboard = useCallback(async () => {
    const variant = rememberedVariant ?? await editorActions.variant.pickForActive(projectVariants);
    if (variant === null) {
      return;
    }
    const clipboardData = await navigator.clipboard.read();
    for (const item of clipboardData) {
      const imageType = item.types.find(type => type.startsWith("image/"));
      if (imageType) {
        const blob = await item.getType(imageType);
        const file = new File([blob], "clipboard.png", { type: imageType });
        await editorActions.variant.importImageForActive([file], variant);
        return;
      }
    }
    toaster.show({ message: t('deviceCapture.clipboardEmpty'), intent: "warning" });
  }, [projectVariants, rememberedVariant, t]);

  const handleNewVariantFromDevice = useCallback(async () => {
    const variant = rememberedVariant ?? await editorActions.variant.pickForActive(projectVariants);
    if (variant === null) {
      return;
    }
    setDeviceCaptureState({ isOpen: true, variant });
  }, [projectVariants, rememberedVariant]);

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
          text: t('menuItem.openImage'),
          label: t('shortcut.ctrlO'),
          onClick: () => {
            setOpenMenu(null);
            void executeCommand(COMMAND_ID.FILE_OPEN_IMAGE, commandContext, undefined);
          },
        },
        {
          icon: "history",
          text: t('menuItem.openRecent'),
          children: (
            <>
              {recentItems.slice(0, 12).map((item) => (
                <MenuItem
                  key={`recent-${item.metaPath}`}
                  text={item.imagePath}
                  style={{ maxWidth: "none" }}
                  onClick={() => {
                    setOpenMenu(null);
                    void editorActions.image.openWithMeta(item.imagePath, { allowHostDelegate: true, source: "other" });
                  }}
                />
              ))}
              <MenuDivider />
              <MenuItem
                icon="trash"
                text={t('menuItem.clearRecent')}
                disabled={recentItems.length === 0}
                onClick={() => {
                  clearRecentInWorkspace();
                  setOpenMenu(null);
                }}
              />
            </>
          ),
          // Keep submenu width unconstrained by target width.
          popoverProps: {
            matchTargetWidth: false,
          },
          onClick: () => {
          },
        },
        {
          icon: "floppy-disk",
          text: t('menuItem.save'),
          label: t('shortcut.ctrlS'),
          disabled: !canSave,
          onClick: () => {
            setOpenMenu(null);
            void executeCommand(COMMAND_ID.FILE_SAVE, commandContext, undefined);
          },
        },
        {
          icon: "floppy-disk",
          text: t('menuItem.saveAll'),
          label: t('shortcut.ctrlShiftS'),
          disabled: !canSaveAll,
          onClick: () => {
            setOpenMenu(null);
            void executeCommand(COMMAND_ID.FILE_SAVE_ALL, commandContext, undefined);
          },
        },
        {
          icon: "edit",
          text: t('menuItem.rename'),
          disabled: !canRenameDocument,
          onClick: () => {
            setOpenMenu(null);
            void executeCommand(COMMAND_ID.FILE_RENAME, commandContext, undefined);
          },
        },
        {
          icon: "cross",
          text: t('menuItem.closeDocument'),
          label: t('shortcut.ctrl2'),
          disabled: !statuses[COMMAND_ID.FILE_CLOSE_ACTIVE].enabled,
          onClick: () => {
            setOpenMenu(null);
            void executeCommand(COMMAND_ID.FILE_CLOSE_ACTIVE, commandContext, undefined);
          },
        },
        {
          icon: "small-cross",
          text: t('menuItem.closeAllDocuments'),
          label: t('shortcut.ctrlShift2'),
          disabled: !statuses[COMMAND_ID.FILE_CLOSE_ALL].enabled,
          onClick: () => {
            setOpenMenu(null);
            void executeCommand(COMMAND_ID.FILE_CLOSE_ALL, commandContext, undefined);
          },
        },
      ],
      edit: [
        {
          icon: "undo",
          text: undoMenuText,
          label: t('shortcut.ctrlZ'),
          disabled: !canUndo,
          onClick: () => {
            setOpenMenu(null);
            void executeCommand(COMMAND_ID.EDIT_UNDO, commandContext, undefined);
          },
        },
        {
          icon: "redo",
          text: redoMenuText,
          label: t('shortcut.ctrlShiftZ'),
          disabled: !canRedo,
          onClick: () => {
            setOpenMenu(null);
            void executeCommand(COMMAND_ID.EDIT_REDO, commandContext, undefined);
          },
        },
      ],
      variant: [
        {
          icon: "duplicate",
          text: t('menuItem.newVariantImage'),
          label: t('shortcut.ctrlAltN'),
          disabled: !canCreateVariantDocument,
          onClick: () => {
            setOpenMenu(null);
            void executeCommand(COMMAND_ID.VARIANT_NEW_DOCUMENT, commandContext, undefined);
          },
        },
        {
          text: t('menuItem.newVariantFromClipboard'),
          disabled: !canCreateVariantDocument,
          onClick: () => {
            setOpenMenu(null);
            void handleNewVariantFromClipboard();
          },
        },
        {
          text: t('menuItem.newVariantFromDevice'),
          disabled: !canCreateVariantDocument,
          onClick: () => {
            setOpenMenu(null);
            void handleNewVariantFromDevice();
          },
        },
        {
          text: t('menuItem.rememberVariantChoice'),
          disabled: !canCreateVariantDocument,
          children: (
            <>
              <MenuItem
                icon={rememberedVariant === null ? "small-tick" : "blank"}
                text={t('menuItem.alwaysAsk')}
                onClick={() => {
                  setRememberedVariant(null);
                  setOpenMenu(null);
                }}
              />
              {projectVariants.map((v) => (
                <MenuItem
                  key={v}
                  icon={rememberedVariant === v ? "small-tick" : "blank"}
                  text={v}
                  onClick={() => {
                    setRememberedVariant(v);
                    setOpenMenu(null);
                  }}
                />
              ))}
            </>
          ),
          popoverProps: {
            matchTargetWidth: false,
          },
        },
        { divider: true },
        {
          icon: "duplicate",
          text: t('menuItem.copyToVariant'),
          disabled: !canCopySelectedPrefabToVariant,
          onClick: () => {
            setOpenMenu(null);
            void executeCommand(COMMAND_ID.VARIANT_COPY_SELECTED_PREFAB, commandContext, undefined);
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
      clearRecentInWorkspace,
      canUndo,
      commandContext,
      documents,
      handleNewVariantFromClipboard,
      handleNewVariantFromDevice,
      projectVariants,
      recentItems,
      redoMenuText,
      rememberedVariant,
      undoMenuText,
      t,
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
    onKeyDown: () => {
      void executeCommand(COMMAND_ID.FILE_OPEN_IMAGE, commandContext, undefined);
    },
  });

  useShortcut({
    id: "editor.save-document",
    scope: "editor",
    combo: "mod+s",
    when: () => statuses[COMMAND_ID.FILE_SAVE].enabled,
    onKeyDown: () => {
      void executeCommand(COMMAND_ID.FILE_SAVE, commandContext, undefined);
    },
  });

  useShortcut({
    id: "editor.save-all-documents",
    scope: "editor",
    combo: "mod+shift+s",
    when: () => statuses[COMMAND_ID.FILE_SAVE_ALL].enabled,
    onKeyDown: () => {
      void executeCommand(COMMAND_ID.FILE_SAVE_ALL, commandContext, undefined);
    },
  });

  useShortcut({
    id: "editor.close-active-document",
    scope: "editor",
    combo: "mod+2",
    when: () => statuses[COMMAND_ID.FILE_CLOSE_ACTIVE].enabled,
    onKeyDown: () => {
      void executeCommand(COMMAND_ID.FILE_CLOSE_ACTIVE, commandContext, undefined);
    },
  });

  useShortcut({
    id: "editor.close-all-document",
    scope: "editor",
    combo: "mod+shift+2",
    when: () => statuses[COMMAND_ID.FILE_CLOSE_ALL].enabled,
    onKeyDown: () => {
      void executeCommand(COMMAND_ID.FILE_CLOSE_ALL, commandContext, undefined);
    },
  });

  useShortcut({
    id: "editor.open-variant-dialog",
    scope: "editor",
    combo: "mod+alt+n",
    when: () => statuses[COMMAND_ID.VARIANT_NEW_DOCUMENT].enabled,
    onKeyDown: () => {
      void executeCommand(COMMAND_ID.VARIANT_NEW_DOCUMENT, commandContext, undefined);
    },
  });

  const renderMenu = () => {
    if (!openMenu) {
      return null;
    }
    return (
      <Menu>
        {menuDefinitions[openMenu].map((item, index) => {
          if ("divider" in item) {
            return <MenuDivider key={`${openMenu}-divider-${index}`} />;
          }
          return (
            <MenuItem
              key={`${openMenu}-${item.text}-${index}`}
              icon={item.icon ?? "blank"}
              text={item.text}
              label={item.label}
              disabled={item.disabled}
              children={item.children}
              popoverProps={item.popoverProps}
              onClick={item.onClick}
            />
          );
        })}
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
          {t('menu.file')}
        </button>
        <button
          ref={editButtonRef}
          type="button"
          style={{ ...triggerStyle, background: openMenu === "edit" ? "#c7d4e0" : "transparent" }}
          onClick={() => toggleMenu("edit")}
          onMouseEnter={() => switchMenuOnHover("edit")}
        >
          {t('menu.edit')}
        </button>
        <button
          ref={variantButtonRef}
          type="button"
          style={{ ...triggerStyle, background: openMenu === "variant" ? "#c7d4e0" : "transparent" }}
          onClick={() => toggleMenu("variant")}
          onMouseEnter={() => switchMenuOnHover("variant")}
        >
          {t('menu.variant')}
        </button>
      </div>
      <div
        onMouseDown={(e) => {
          e.preventDefault();
          void executeCommand(COMMAND_ID.APP_OPEN_COMMAND_PALETTE, commandContext, undefined);
        }}
      >
        <InputGroup
          leftIcon="search"
          value=""
          readOnly
          placeholder={t('placeholder.searchCommands')}
          rightElement={<div style={{ padding: "6px 10px", color: "#5c7080", fontSize: 12 }}>{t('shortcut.ctrlShiftP')}</div>}
        />
      </div>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "flex-end" }}>
        <HTMLSelect
          minimal
          value={language}
          onChange={(e) => setLanguage(e.target.value as typeof language)}
          options={SUPPORTED_LANGUAGES.map((lang: string) => ({ value: lang, label: lang === 'zh-CN' ? '中文' : 'English' }))}
          style={{ height: 24, fontSize: 12 }}
        />
      </div>
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
        title={t('dialog.openImage')}
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
        showDeviceCapture={false}
      />
      <DeviceCaptureDialog
        isOpen={deviceCaptureState.isOpen}
        onClose={() => setDeviceCaptureState({ isOpen: false, variant: null })}
        onImport={handleDeviceCaptureImport}
      />
    </div>
  );
};
