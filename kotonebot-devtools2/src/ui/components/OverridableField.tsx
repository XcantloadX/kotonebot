import React from "react";
import { Classes, Icon, Tooltip } from "@blueprintjs/core";

interface OverridableFieldProps {
  /** 当前字段是否已配置。`true` 为实心圆点，`false` 为空心圆点。 */
  isSet: boolean;
  /** 从未配置切换为已配置时触发。 */
  onSet: () => void;
  /** 从已配置切换为未配置时触发。 */
  onUnset: () => void;
  /** 右侧插槽内容，通常为具体属性编辑器。 */
  children: React.ReactNode;
  /** 是否禁用切换交互。 */
  disabled?: boolean;
}

/** 
 * 可覆盖字段组件，适用于属性编辑器中某些字段既可以使用默认值，也可以由用户自定义配置的场景。
 * 
 * 左侧提供可切换的“是否配置”圆点，右侧渲染自定义编辑内容。
 */
export const OverridableField: React.FC<OverridableFieldProps> = ({
  isSet,
  onSet,
  onUnset,
  children,
  disabled = false,
}) => {
  const renderDot = (filled: boolean) => (
    <span
      style={{
        width: 10,
        height: 10,
        borderRadius: "50%",
        border: "1px solid #5c7080",
        backgroundColor: filled ? "#5c7080" : "transparent",
        display: "inline-block",
      }}
    />
  );

  const handleToggle = () => {
    if (disabled) {
      return;
    }
    if (isSet) {
      onUnset();
      return;
    }
    onSet();
  };

  return (
    <div style={{ display: "flex", alignItems: "flex-start", gap: 8 }}>
      <Tooltip
        position="left"
        interactionKind="hover"
        hoverOpenDelay={0}
        hoverCloseDelay={40}
        popoverClassName="kb-overridable-tooltip"
        content={
          <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
              {renderDot(false)}
              <span style={{ display: "inline-flex", alignItems: "center", gap: 4 }}>
                <span>不配置</span>
                <Tooltip
                  content="将使用框架或代码中配置的默认值"
                  position="right"
                  interactionKind="hover-target"
                  hoverOpenDelay={0}
                  hoverCloseDelay={40}
                >
                  <span style={{ display: "inline-flex", alignItems: "center", cursor: "help" }}>
                    <Icon icon="help" size={12} />
                  </span>
                </Tooltip>
              </span>
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
              {renderDot(true)}
              <span>自定义配置</span>
            </div>
          </div>
        }
      >
        <button
          type="button"
          className={`${Classes.BUTTON} ${Classes.MINIMAL} ${Classes.SMALL}`}
          onClick={handleToggle}
          style={{
            width: 18,
            height: 18,
            padding: 0,
            marginTop: 5,
            minWidth: 18,
            minHeight: 18,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            lineHeight: 0,
          }}
        >
          <span style={{ display: "block", lineHeight: 0 }}>{renderDot(isSet)}</span>
        </button>
      </Tooltip>
      <div style={{ flex: 1, minWidth: 0 }}>{children}</div>
    </div>
  );
};
