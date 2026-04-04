import React from "react";
import { Button } from "@blueprintjs/core";
import type { ButtonProps } from "@blueprintjs/core";

export type ShortcutButtonProps = ButtonProps & {
  /**
   * 可选的快捷键提示文本。
   * 传入后会在按钮文案右侧渲染角标，例如 Enter / Esc。
   */
  shortcutText?: string;
};

/**
 * 在 Blueprint Button 基础上增加快捷键角标展示能力。
 * 除 `shortcutText` 外，其他 props 与 Button 完全一致。
 */
export const ShortcutButton: React.FC<ShortcutButtonProps> = ({
  shortcutText,
  children,
  ...buttonProps
}) => {
  return (
    <Button {...buttonProps}>
      {children}
      {shortcutText ? (
        <span
          style={{
            marginLeft: 8,
            padding: "2px 6px",
            background: "rgba(255,255,255,0.2)",
            borderRadius: 3,
            fontSize: 11,
            fontFamily: "monospace",
          }}
        >
          {shortcutText}
        </span>
      ) : null}
    </Button>
  );
};
