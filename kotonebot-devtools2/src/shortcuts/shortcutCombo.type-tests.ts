import type { AssertShortcutCombo, IsValidShortcutCombo, ValidateShortcutCombo } from "./shortcutCombo";

type ExpectTrue<T extends true> = T;
type ExpectFalse<T extends false> = T;

export type TypeAssertValidModS = ExpectTrue<IsValidShortcutCombo<"mod+s">>;
export type TypeAssertValidShiftEscape = ExpectTrue<IsValidShortcutCombo<"shift+escape">>;
export type TypeAssertValidSingleKey = ExpectTrue<IsValidShortcutCombo<"v">>;
export type TypeAssertValidDigit = ExpectTrue<IsValidShortcutCombo<"mod+2">>;
export type TypeAssertInvalidNoKey = ExpectFalse<IsValidShortcutCombo<"mod+shift">>;
export type TypeAssertInvalidTwoKeys = ExpectFalse<IsValidShortcutCombo<"mod+s+v">>;
export type TypeAssertInvalidUnknownToken = ExpectFalse<IsValidShortcutCombo<"mod+capslock">>;
export type TypeAssertInvalidEmptyPart = ExpectFalse<IsValidShortcutCombo<"mod++s">>;

export const validComboA: AssertShortcutCombo<"mod+s"> = "mod+s";
export const validComboB: AssertShortcutCombo<"shift+escape"> = "shift+escape";
export const validComboC: AssertShortcutCombo<"v"> = "v";
export const validComboD: AssertShortcutCombo<"mod+2"> = "mod+2";
export const genericStringCombo: ValidateShortcutCombo<string> = "anything";
export const validatedLiteralCombo: ValidateShortcutCombo<"mod+o"> = "mod+o";

// @ts-expect-error combo 必须包含且仅包含一个 key
export const invalidComboNoKey: AssertShortcutCombo<"mod+shift"> = "mod+shift";
// @ts-expect-error combo 不能包含多个 key
export const invalidComboTwoKeys: AssertShortcutCombo<"mod+s+v"> = "mod+s+v";
// @ts-expect-error key 必须在 KeyToken 列表中
export const invalidComboUnknownKey: AssertShortcutCombo<"mod+capslock"> = "mod+capslock";
// @ts-expect-error token 不能是空字符串
export const invalidComboEmptyToken: AssertShortcutCombo<"mod++s"> = "mod++s";
