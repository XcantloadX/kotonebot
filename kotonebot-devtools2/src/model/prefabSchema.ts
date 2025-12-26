export type PropKind = "rect" | "point" | "image" | "bool" | "float" | "int" | "str";

export interface EditorPropSchema {
  kind: PropKind;
  label: string;
  description?: string;
  default_value?: any;
  min?: number;
  max?: number;
}

export interface PrefabMetadata {
  id: string;
  name: string;
  description: string;
  primary_prop?: string;
  icon?: string;
  shortcut?: string;
  props: Record<string, EditorPropSchema>;
}

export interface PrefabSchema {
  version: number;
  prefabs: Record<string, PrefabMetadata>;
}
