import React, { createContext, useCallback, useContext, useMemo, useState } from "react";
import { Button, Classes, Dialog, HTMLSelect, InputGroup, Intent } from "@blueprintjs/core";
import i18n from "../i18n";

export interface MessageBoxButton<TValue extends string = string> {
  value: TValue;
  text: string;
  intent?: Intent;
  disabled?: boolean;
}

export interface MessageBoxOptions<TValue extends string = string> {
  title: string;
  content: React.ReactNode;
  buttons: Array<MessageBoxButton<TValue>>;
  dismissValue?: TValue;
  canEscapeKeyClose?: boolean;
  canOutsideClickClose?: boolean;
}

interface PendingMessageBoxRequest {
  options: MessageBoxOptions;
  resolve: (value: string) => void;
}

interface BinaryMessageBoxOptions {
  title: string;
  content: React.ReactNode;
  yesText?: string;
  noText?: string;
  yesIntent?: Intent;
  noIntent?: Intent;
}

interface ConfirmCancelMessageBoxOptions {
  title: string;
  content: React.ReactNode;
  confirmText?: string;
  cancelText?: string;
  confirmIntent?: Intent;
  cancelIntent?: Intent;
}

interface OkMessageBoxOptions {
  title: string;
  content: React.ReactNode;
  okText?: string;
  okIntent?: Intent;
}

interface PromptMessageBoxOptions {
  title: string;
  content?: React.ReactNode;
  defaultValue?: string;
  placeholder?: string;
  confirmText?: string;
  cancelText?: string;
  confirmIntent?: Intent;
  cancelIntent?: Intent;
}

interface SelectMessageBoxOptions {
  title: string;
  content?: React.ReactNode;
  options: string[];
  defaultValue?: string;
  confirmText?: string;
  cancelText?: string;
  confirmIntent?: Intent;
  cancelIntent?: Intent;
}

export interface MessageBoxApi {
  show: <TValue extends string = string>(options: MessageBoxOptions<TValue>) => Promise<TValue>;
  yes_no: (options: BinaryMessageBoxOptions) => Promise<boolean>;
  confirm_cancel: (options: ConfirmCancelMessageBoxOptions) => Promise<boolean>;
  ok: (options: OkMessageBoxOptions) => Promise<void>;
  prompt: (options: PromptMessageBoxOptions) => Promise<string | null>;
  select: (options: SelectMessageBoxOptions) => Promise<string | null>;
}

const MessageBoxContext = createContext<MessageBoxApi | null>(null);
let globalMessageBoxApi: MessageBoxApi | null = null;

export function setGlobalMessageBox(api: MessageBoxApi | null): void {
  globalMessageBoxApi = api;
}

export function getGlobalMessageBox(): MessageBoxApi | null {
  return globalMessageBoxApi;
}

export function getGlobalMessageBoxOrThrow(): MessageBoxApi {
  const api = getGlobalMessageBox();
  if (!api) {
    throw new Error("MessageBox API is not initialized");
  }
  return api;
}

export const messageBox: MessageBoxApi = {
  show: (options) => getGlobalMessageBoxOrThrow().show(options),
  yes_no: (options) => getGlobalMessageBoxOrThrow().yes_no(options),
  confirm_cancel: (options) => getGlobalMessageBoxOrThrow().confirm_cancel(options),
  ok: (options) => getGlobalMessageBoxOrThrow().ok(options),
  prompt: (options) => getGlobalMessageBoxOrThrow().prompt(options),
  select: (options) => getGlobalMessageBoxOrThrow().select(options),
};

export const useMessageBox = (): MessageBoxApi => {
  const value = useContext(MessageBoxContext);
  if (!value) {
    throw new Error("useMessageBox must be used within MessageBoxProvider");
  }
  return value;
};

export const MessageBoxProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [queue, setQueue] = useState<PendingMessageBoxRequest[]>([]);
  const current = queue[0] ?? null;

  const settleCurrent = useCallback((value: string) => {
    setQueue((prev) => {
      const [head, ...rest] = prev;
      if (!head) {
        throw new Error("No pending message box request");
      }
      head.resolve(value);
      return rest;
    });
  }, []);

  const show = useCallback(
    <TValue extends string = string>(options: MessageBoxOptions<TValue>): Promise<TValue> => {
      if (options.buttons.length === 0) {
        throw new Error("MessageBox requires at least one button");
      }
      return new Promise<TValue>((resolve) => {
        setQueue((prev) => [
          ...prev,
          {
            options: options as MessageBoxOptions,
            resolve: (value: string) => resolve(value as TValue),
          },
        ]);
      });
    },
    []
  );

  const yes_no = useCallback(
    async (options: BinaryMessageBoxOptions): Promise<boolean> => {
      const result = await show<"yes" | "no">({
        title: options.title,
        content: options.content,
        buttons: [
          { value: "yes", text: options.yesText ?? i18n.t('dialog.yes'), intent: options.yesIntent ?? "primary" },
          { value: "no", text: options.noText ?? i18n.t('dialog.no'), intent: options.noIntent ?? "none" },
        ],
      });
      return result === "yes";
    },
    [show]
  );

  const confirm_cancel = useCallback(
    async (options: ConfirmCancelMessageBoxOptions): Promise<boolean> => {
      const result = await show<"confirm" | "cancel">({
        title: options.title,
        content: options.content,
        buttons: [
          {
            value: "confirm",
            text: options.confirmText ?? i18n.t('dialog.confirm'),
            intent: options.confirmIntent ?? "primary",
          },
          {
            value: "cancel",
            text: options.cancelText ?? i18n.t('dialog.cancel'),
            intent: options.cancelIntent ?? "none",
          },
        ],
      });
      return result === "confirm";
    },
    [show]
  );

  const ok = useCallback(
    async (options: OkMessageBoxOptions): Promise<void> => {
      await show<"ok">({
        title: options.title,
        content: options.content,
        buttons: [{ value: "ok", text: options.okText ?? i18n.t('dialog.ok'), intent: options.okIntent ?? "primary" }],
      });
    },
    [show]
  );

  const prompt = useCallback(
    async (options: PromptMessageBoxOptions): Promise<string | null> => {
      let value = options.defaultValue ?? "";
      const result = await show<"confirm" | "cancel">({
        title: options.title,
        content: (
          <div style={{ display: "grid", gap: 10 }}>
            {options.content ? <div>{options.content}</div> : null}
            <InputGroup
              autoFocus
              defaultValue={value}
              placeholder={options.placeholder}
              onChange={(e) => {
                value = (e.target as HTMLInputElement).value;
              }}
            />
          </div>
        ),
        buttons: [
          {
            value: "confirm",
            text: options.confirmText ?? i18n.t('dialog.confirm'),
            intent: options.confirmIntent ?? "primary",
          },
          {
            value: "cancel",
            text: options.cancelText ?? i18n.t('dialog.cancel'),
            intent: options.cancelIntent ?? "none",
          },
        ],
        dismissValue: "cancel",
        canEscapeKeyClose: true,
        canOutsideClickClose: false,
      });
      if (result === "cancel") {
        return null;
      }
      return value;
    },
    [show]
  );

  const select = useCallback(
    async (options: SelectMessageBoxOptions): Promise<string | null> => {
      if (options.options.length === 0) {
        throw new Error("select requires at least one option");
      }
      let value = options.defaultValue ?? options.options[0];
      if (!options.options.includes(value)) {
        throw new Error("defaultValue must be one of options");
      }
      const result = await show<"confirm" | "cancel">({
        title: options.title,
        content: (
          <div style={{ display: "grid", gap: 10 }}>
            {options.content ? <div>{options.content}</div> : null}
            <HTMLSelect
              fill
              defaultValue={value}
              options={options.options}
              onChange={(e) => {
                value = (e.target as HTMLSelectElement).value;
              }}
            />
          </div>
        ),
        buttons: [
          {
            value: "confirm",
            text: options.confirmText ?? i18n.t('dialog.confirm'),
            intent: options.confirmIntent ?? "primary",
          },
          {
            value: "cancel",
            text: options.cancelText ?? i18n.t('dialog.cancel'),
            intent: options.cancelIntent ?? "none",
          },
        ],
        dismissValue: "cancel",
        canEscapeKeyClose: true,
        canOutsideClickClose: false,
      });
      if (result === "cancel") {
        return null;
      }
      return value;
    },
    [show]
  );

  const api = useMemo<MessageBoxApi>(
    () => ({
      show,
      yes_no,
      confirm_cancel,
      ok,
      prompt,
      select,
    }),
    [confirm_cancel, ok, prompt, select, show, yes_no]
  );

  React.useEffect(() => {
    setGlobalMessageBox(api);
    return () => {
      setGlobalMessageBox(null);
    };
  }, [api]);

  return (
    <MessageBoxContext.Provider value={api}>
      {children}
      <Dialog
        isOpen={!!current}
        title={current?.options.title}
        portalClassName="kb-message-box-portal"
        onClose={() => {
          if (current?.options.dismissValue) {
            settleCurrent(current.options.dismissValue);
          }
        }}
        canEscapeKeyClose={current?.options.canEscapeKeyClose ?? false}
        canOutsideClickClose={current?.options.canOutsideClickClose ?? false}
      >
        <div className={Classes.DIALOG_BODY}>{current?.options.content}</div>
        <div className={Classes.DIALOG_FOOTER}>
          <div className={Classes.DIALOG_FOOTER_ACTIONS}>
            {current?.options.buttons.map((button) => (
              <Button
                key={button.value}
                intent={button.intent}
                disabled={button.disabled}
                onClick={() => settleCurrent(button.value)}
              >
                {button.text}
              </Button>
            ))}
          </div>
        </div>
      </Dialog>
    </MessageBoxContext.Provider>
  );
};
