import React from 'react';
import { InputGroup, Button, InputGroupProps } from '@blueprintjs/core';

export interface ClearableInputGroupProps extends InputGroupProps {
  onClear?: () => void;
}

const ClearableInputGroup: React.FC<ClearableInputGroupProps> = ({ onClear, rightElement, value, ...rest }) => {
  const showClear = typeof value === 'string' ? value.length > 0 : !!value;
  const clearButton = onClear ? (
    <Button minimal small icon="cross" aria-label="Clear" onClick={() => onClear()} />
  ) : undefined;

  return (
    <InputGroup
      {...rest}
      value={value}
      rightElement={showClear ? clearButton : rightElement}
    />
  );
};

export default ClearableInputGroup;
