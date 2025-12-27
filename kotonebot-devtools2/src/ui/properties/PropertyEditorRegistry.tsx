import React from 'react';
import { FormGroup, InputGroup, NumericInput, Switch, Button, Tooltip, Icon, Checkbox } from '@blueprintjs/core';
import { PropValue } from '../../model/metaV2';
import { EditorPropSchema } from '../../model/prefabSchema';

export interface PropertyEditorProps {
    propKey: string;
    value: PropValue | undefined;
    schema?: EditorPropSchema;
    onChange: (value: any) => void;
    onEditGeometry?: (kind: "rect" | "point" | "image") => void;
}

const LabelWithCheckbox: React.FC<{ schema?: EditorPropSchema; propKey?: string; value: any; onChange: (v: any) => void }> = ({ schema, propKey, value, onChange }) => {
    const text = schema?.label || propKey || '';
    const hasValue = value !== undefined;

    const handleToggle = (e: React.FormEvent<HTMLInputElement>) => {
        const checked = (e.currentTarget as HTMLInputElement).checked;
        if (checked) {
            // unchecked -> checked: 设置为 prop 默认值
            if (schema?.default_value === undefined) {
                console.warn(`Property "${propKey}" has no default value in schema.`);
            }
            onChange(schema?.default_value);
        } else {
            // checked -> unchecked: set to undefined
            onChange(undefined);
        }
    };

    const labelContent = (
        <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}>
            <span>{text}</span>
            {schema?.description && (
                <Tooltip content={schema.description} position="right">
                    <span style={{ display: 'inline-flex', alignItems: 'center' }}>
                        <Icon icon="help" size={14} style={{ color: '#2b6f9e' }} />
                    </span>
                </Tooltip>
            )}
        </span>
    );

    const checkbox = (
        <Checkbox
            checked={hasValue}
            onChange={handleToggle}
            labelElement={labelContent}
        />
    );

    return (
        <div style={{ display: 'inline-flex', alignItems: 'center' }}>
            {schema && hasValue ? (
                <Tooltip content={"关闭将会设置此属性为空，具体值将取决于运行时默认值"} position="right">
                    {checkbox}
                </Tooltip>
            ) : (
                checkbox
            )}
        </div>
    );
};

export const BoolEditor: React.FC<PropertyEditorProps> = ({ propKey, value, schema, onChange }) => (
    <FormGroup label={<LabelWithCheckbox schema={schema} propKey={propKey} value={value} onChange={onChange} />}>
        {value !== undefined ? (
            <Switch
                checked={value as boolean}
                onChange={e => onChange(e.currentTarget.checked)}
            />
        ) : null}
    </FormGroup>
);

export const NumberEditor: React.FC<PropertyEditorProps> = ({ propKey, value, schema, onChange }) => (
    <FormGroup label={<LabelWithCheckbox schema={schema} propKey={propKey} value={value} onChange={onChange} />}>
        {value !== undefined ? (
            <NumericInput 
                value={value as number} 
                onValueChange={v => onChange(v)} 
                min={schema?.min}
                max={schema?.max}
                fill
            />
        ) : null}
    </FormGroup>
);

export const StringEditor: React.FC<PropertyEditorProps> = ({ propKey, value, schema, onChange }) => (
    <FormGroup label={<LabelWithCheckbox schema={schema} propKey={propKey} value={value} onChange={onChange} />}>
        {value !== undefined ? (
            <InputGroup 
                value={value as string} 
                onChange={e => onChange(e.target.value)} 
            />
        ) : null}
    </FormGroup>
);

export const GeometryEditor: React.FC<PropertyEditorProps> = ({ propKey, value, schema, onEditGeometry, onChange }) => {
    const rectVal = value as any;
    const kind = schema?.kind || (value as any)?.kind;
    const label = schema?.label || propKey;
    
    const toNumber = (v: string) => {
        const n = parseFloat(v);
        return Number.isNaN(n) ? 0 : n;
    };

    return (
        <FormGroup label={<LabelWithCheckbox schema={schema} propKey={propKey} value={value} onChange={onChange} />}>
            {value !== undefined ? (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                    {/* when no value, show Not set + pick button; when value exists, hide textual preview and show inputs with button to the right */}
                    {!rectVal && (
                        <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                            <div style={{ flex: 1, fontSize: 12, color: '#a7b6c2' }}>Not set</div>
                            {kind && (
                                <Button icon="select" variant='minimal' onClick={() => onEditGeometry?.(kind)} />
                            )}
                        </div>
                    )}

                    {kind === 'point' && rectVal && (
                        <div style={{ display: 'flex', gap: 6, alignItems: 'end' }}>
                            <div style={{ display: 'flex', flexDirection: 'column', width: 90 }}>
                                <div style={{ fontSize: 11, color: '#8a9ba8', marginBottom: 4 }}>X</div>
                                <InputGroup
                                    type="number"
                                    value={(rectVal?.x ?? 0).toString()}
                                    onChange={e => onChange({ ...(rectVal || {}), x: toNumber(e.target.value) })}
                                />
                            </div>
                            <div style={{ display: 'flex', flexDirection: 'column', width: 90 }}>
                                <div style={{ fontSize: 11, color: '#8a9ba8', marginBottom: 4 }}>Y</div>
                                <InputGroup
                                    type="number"
                                    value={(rectVal?.y ?? 0).toString()}
                                    onChange={e => onChange({ ...(rectVal || {}), y: toNumber(e.target.value) })}
                                />
                            </div>
                            <div style={{ marginLeft: 'auto' }}>
                                <Button icon="select" variant='minimal' onClick={() => onEditGeometry?.(kind)} />
                            </div>
                        </div>
                    )}

                    {(kind === 'rect' || kind === 'image') && rectVal && (
                        <div style={{ display: 'flex', gap: 6, alignItems: 'end' }}>
                            <div style={{ display: 'flex', flexDirection: 'column', width: 72 }}>
                                <div style={{ fontSize: 11, color: '#8a9ba8', marginBottom: 4 }}>x1</div>
                                <InputGroup
                                    type="number"
                                    value={(rectVal?.x1 ?? 0).toString()}
                                    onChange={e => onChange({ ...(rectVal || {}), x1: toNumber(e.target.value) })}
                                />
                            </div>
                            <div style={{ display: 'flex', flexDirection: 'column', width: 72 }}>
                                <div style={{ fontSize: 11, color: '#8a9ba8', marginBottom: 4 }}>y1</div>
                                <InputGroup
                                    type="number"
                                    value={(rectVal?.y1 ?? 0).toString()}
                                    onChange={e => onChange({ ...(rectVal || {}), y1: toNumber(e.target.value) })}
                                />
                            </div>
                            <div style={{ display: 'flex', flexDirection: 'column', width: 72 }}>
                                <div style={{ fontSize: 11, color: '#8a9ba8', marginBottom: 4 }}>x2</div>
                                <InputGroup
                                    type="number"
                                    value={(rectVal?.x2 ?? 0).toString()}
                                    onChange={e => onChange({ ...(rectVal || {}), x2: toNumber(e.target.value) })}
                                />
                            </div>
                            <div style={{ display: 'flex', flexDirection: 'column', width: 72 }}>
                                <div style={{ fontSize: 11, color: '#8a9ba8', marginBottom: 4 }}>y2</div>
                                <InputGroup
                                    type="number"
                                    value={(rectVal?.y2 ?? 0).toString()}
                                    onChange={e => onChange({ ...(rectVal || {}), y2: toNumber(e.target.value) })}
                                />
                            </div>
                            <div style={{ marginLeft: 'auto' }}>
                                <Button icon="select" variant='minimal' onClick={() => onEditGeometry?.(kind)} />
                            </div>
                        </div>
                    )}
                </div>
            ) : null}
        </FormGroup>
    );
};

export const getEditorForType = (kind: string) => {
    switch (kind) {
        case 'bool': return BoolEditor;
        case 'int':
        case 'float':
        case 'number': return NumberEditor;
        case 'str':
        case 'string': return StringEditor;
        case 'rect':
        case 'image':
        case 'point': return GeometryEditor;
        default: return null;
    }
};
