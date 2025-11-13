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
                            title: '提示矩形',
                            render: {
                                type: 'checkbox',
                                value: definition.useHintRect,
                                onChange: (value) => onUpdate({ useHintRect: value }),
                            }
                        }
                    ]
                }
            ]}
        />
    );
};

export default TemplateToolProperties;
