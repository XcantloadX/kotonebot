import React from 'react';
import { Definition } from '../../types/definitions';
import PropertyGrid from '../../../../components/PropertyGrid';

const TemplateToolProperties: React.FC<{ definition: Definition, onUpdate: (changes: Partial<Definition>) => void }> = ({ definition, onUpdate }) => {
    if (definition.type !== 'template') {
        return null;
    }
    return (
        <PropertyGrid
            properties={[
                {
                    title: '模板',
                    foldable: true,
                    properties: [
                        {
                            title: '固定位置',
                            render: {
                                type: 'checkbox',
                                value: definition.fixed,
                                onChange: (value) => onUpdate({ fixed: value }),
                            }
                        },
                        {
                            title: '阈值',
                            render: {
                                type: 'number',
                                value: definition.threshold || '',
                                placeholder: '默认',
                                onChange: (value: string | number) => onUpdate({ threshold: value === '' ? null : Number(value) }),
                                min: 0,
                                max: 1,
                                step: 0.01
                            }
                        },
                        {
                            title: '颜色识别',
                            render: {
                                type: 'checkbox',
                                value: definition.colored ?? false,
                                onChange: (value: boolean) => onUpdate({ colored: value }),
                            }
                        }
                    ]
                }
            ]}
        />
    );
};

export default TemplateToolProperties;
