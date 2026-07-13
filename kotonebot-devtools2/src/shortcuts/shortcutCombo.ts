type ModifierToken = "ctrl" | "control" | "meta" | "cmd" | "command" | "shift" | "alt" | "option" | "mod";

type Letter =
  | "a" | "b" | "c" | "d" | "e" | "f" | "g" | "h" | "i" | "j" | "k" | "l" | "m"
  | "n" | "o" | "p" | "q" | "r" | "s" | "t" | "u" | "v" | "w" | "x" | "y" | "z";
type Digit = "0" | "1" | "2" | "3" | "4" | "5" | "6" | "7" | "8" | "9";
type FunctionKey = "f1" | "f2" | "f3" | "f4" | "f5" | "f6" | "f7" | "f8" | "f9" | "f10" | "f11" | "f12";
type NamedKey =
  | "space"
  | "enter"
  | "tab"
  | "escape"
  | "backspace"
  | "delete"
  | "up"
  | "down"
  | "left"
  | "right"
  | "comma";

type KeyToken = Letter | Digit | FunctionKey | NamedKey;

type Split<S extends string> = S extends `${infer Head}+${infer Tail}` ? [Head, ...Split<Tail>] : [S];

type IsModifier<Token extends string> = Token extends ModifierToken ? true : false;
type IsKey<Token extends string> = Token extends KeyToken ? true : false;

type AllTokensValid<Tokens extends string[]> =
  Tokens extends [infer Head extends string, ...infer Tail extends string[]]
    ? IsModifier<Head> extends true
      ? AllTokensValid<Tail>
      : IsKey<Head> extends true
        ? AllTokensValid<Tail>
        : false
    : true;

type HasEmptyToken<Tokens extends string[]> =
  Tokens extends [infer Head extends string, ...infer Tail extends string[]]
    ? Head extends ""
      ? true
      : HasEmptyToken<Tail>
    : false;

type KeyCount<Tokens extends string[], Count extends 0[] = []> =
  Tokens extends [infer Head extends string, ...infer Tail extends string[]]
    ? IsModifier<Head> extends true
      ? KeyCount<Tail, Count>
      : KeyCount<Tail, [0, ...Count]>
    : Count["length"];

type IsExactlyOneKey<Tokens extends string[]> = KeyCount<Tokens> extends 1 ? true : false;

type IsValidShortcutCombo<S extends string> =
  HasEmptyToken<Split<S>> extends true
    ? false
    : AllTokensValid<Split<S>> extends true
      ? IsExactlyOneKey<Split<S>>
      : false;

export type ShortcutCombo = string;
export type AssertShortcutCombo<S extends string> = IsValidShortcutCombo<S> extends true ? S : never;
export type ValidateShortcutCombo<S extends string> = string extends S ? string : AssertShortcutCombo<S>;

export type { IsValidShortcutCombo, KeyToken, ModifierToken };
