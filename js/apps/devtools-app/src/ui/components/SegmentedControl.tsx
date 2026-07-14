import { Button, ButtonGroup } from '@blueprintjs/core';

type SegmentedValue = string | number | boolean | null;

export type SegmentedOption<T extends SegmentedValue> = {
  label: string;
  value: T;
};

type SegmentedControlProps<T extends SegmentedValue> = {
  options: readonly SegmentedOption<T>[];
  value: T;
  onChange: (value: T) => void;
  fill?: boolean;
  small?: boolean;
};

export function SegmentedControl<T extends SegmentedValue>({
  options,
  value,
  onChange,
  fill = true,
  small = false,
}: SegmentedControlProps<T>) {
  return (
    <ButtonGroup fill={fill}>
      {options.map((option) => (
        <Button
          key={String(option.value)}
          small={small}
          outlined
          active={option.value === value}
          onClick={() => onChange(option.value)}
          text={option.label}
        />
      ))}
    </ButtonGroup>
  );
}
