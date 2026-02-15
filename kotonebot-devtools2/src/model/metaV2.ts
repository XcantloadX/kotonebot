export type ResourceType = "template" | "prefab" | "hint-box" | "hint-point";

export type RectValue = { kind: "rect"; x1: number; y1: number; x2: number; y2: number };
export type PointValue = { kind: "point"; x: number; y: number };
export type ImageValue = { kind: "image"; x1: number; y1: number; x2: number; y2: number };
export type BoolValue = boolean;
export type NumberValue = number;
export type StringValue = string;

export type PropValue = RectValue | PointValue | ImageValue | BoolValue | NumberValue | StringValue;

export interface DefinitionV2 {
  type: ResourceType;
  name?: string;
  variant?: string;
  displayName?: string;
  description?: string;
  prefab_id?: string;
  props: Record<string, PropValue>;
}

export interface MetaV2 {
  version: 2;
  definitions: Record<string, DefinitionV2>;
}
