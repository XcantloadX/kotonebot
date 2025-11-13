import { BsPinMap } from 'react-icons/bs';
import { ToolPlugin } from '../types';
import { Annotation } from '../../../../components/ImageEditor/types';
import { HintPointDefinition } from '../../types/definitions';

const hintPointTool: ToolPlugin = {
    id: 'hint-point',
    name: 'HintPoint 工具',
    hotkey: 'P',
    icon: <BsPinMap size={24} />,
    editorTool: 'point',
    createDefinition: (annotation: Annotation): HintPointDefinition => {
        if (annotation.type !== 'point') {
            throw new Error('HintPoint tool must be used with a point annotation');
        }
        return {
            name: `hintpoint_${annotation.id.substring(0, 4)}`,
            displayName: '',
            description: '',
            type: 'hint-point',
            annotationId: annotation.id,
        };
    },
    // PropertiesComponent will be implemented in a later task
};

export default hintPointTool;
