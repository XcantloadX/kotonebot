import React from 'react';
import { FormGroup, InputGroup, Switch, Button, Tooltip, Icon } from '@blueprintjs/core';
import { PropValue } from '../../model/metaV2';
import { EditorPropSchema } from '../../model/prefabSchema';

export interface PropertyEditorProps {
    propKey: string;
    value: PropValue | undefined;
    schema?: EditorPropSchema;
    onChange: (value: any) => void;
    onEditGeometry?: (kind: "rect" | "point" | "image") => void;
}

const PropertyLabel: React.FC<{ schema?: EditorPropSchema; propKey?: string }> = ({ schema, propKey }) => {
    const text = schema?.label || propKey || '';
    return (
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
};

export const BoolEditor: React.FC<PropertyEditorProps> = ({ propKey, value, schema, onChange }) => (
    <FormGroup label={<PropertyLabel schema={schema} propKey={propKey} />}>
        {value !== undefined ? (
            <Switch
                checked={value as boolean}
                onChange={e => onChange(e.currentTarget.checked)}
            />
        ) : null}
    </FormGroup>
);

export const NumberEditor: React.FC<PropertyEditorProps> = ({ propKey, value, schema, onChange }) => {
    const currentValue = typeof value === 'number' ? value : 0;
    const isInt = schema?.kind === 'int';
    const [draft, setDraft] = React.useState<string>(currentValue.toString());
    const [isFocused, setIsFocused] = React.useState(false);

    React.useEffect(() => {
        if (!isFocused) {
            setDraft(currentValue.toString());
        }
    }, [currentValue, isFocused]);

    const parseDraft = (raw: string): number | null => {
        const text = raw.trim();
        if (text === '' || text === '-' || text === '.' || text === '-.') {
            return null;
        }
        const parsed = Number(text);
        if (!Number.isFinite(parsed)) {
            return null;
        }
        return isInt ? Math.trunc(parsed) : parsed;
    };

    const commit = (raw: string) => {
        const parsed = parseDraft(raw);
        if (parsed === null) {
            return;
        }
        onChange(parsed);
    };

    return (
        <FormGroup label={<PropertyLabel schema={schema} propKey={propKey} />}>
            {value !== undefined ? (
                <InputGroup
                    type="number"
                    value={draft}
                    min={schema?.min}
                    max={schema?.max}
                    step={isInt ? 1 : 'any'}
                    onFocus={() => setIsFocused(true)}
                    onChange={e => {
                        const next = e.target.value;
                        setDraft(next);
                        commit(next);
                    }}
                    onBlur={() => {
                        setIsFocused(false);
                        const parsed = parseDraft(draft);
                        if (parsed === null) {
                            setDraft(currentValue.toString());
                            return;
                        }
                        onChange(parsed);
                        setDraft(parsed.toString());
                    }}
                />
            ) : null}
        </FormGroup>
    );
};

export const StringEditor: React.FC<PropertyEditorProps> = ({ propKey, value, schema, onChange }) => (
    <FormGroup label={<PropertyLabel schema={schema} propKey={propKey} />}>
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
    
    const toNumber = (v: string) => {
        const n = parseFloat(v);
        return Number.isNaN(n) ? 0 : n;
    };

    return (
        <FormGroup label={<PropertyLabel schema={schema} propKey={propKey} />}>
            {value !== undefined ? (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
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
