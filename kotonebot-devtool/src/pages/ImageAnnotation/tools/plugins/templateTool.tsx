import { BsCardImage } from 'react-icons/bs';
import { ToolPlugin } from '../types';
import { Annotation } from '../../../../components/ImageEditor/types';
import { TemplateDefinition } from '../../types/definitions';

import TemplateToolProperties from './TemplateToolProperties';

const templateTool: ToolPlugin = {
    id: 'template',
    name: '模板工具',
    hotkey: 'T',
    icon: <BsCardImage size={24} />,
    editorTool: 'rect',
    createDefinition: (annotation: Annotation): TemplateDefinition => {
        if (annotation.type !== 'rect') {
            throw new Error('Template tool must be used with a rect annotation');
        }
        return {
            name: `template_${annotation.id.substring(0, 4)}`,
            displayName: '',
            description: '',
            type: 'template',
            annotationId: annotation.id,
            fixed: false,
            threshold: null,
            colored: null,
        };
    },
    PropertiesComponent: TemplateToolProperties,
};

export default templateTool;
