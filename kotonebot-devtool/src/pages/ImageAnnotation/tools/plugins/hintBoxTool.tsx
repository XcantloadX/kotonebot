import { BsQuestionSquare } from 'react-icons/bs';
import { ToolPlugin } from '../types';
import { Annotation } from '../../../../components/ImageEditor/types';
import { HintBoxDefinition } from '../../types/definitions';

const hintBoxTool: ToolPlugin = {
    id: 'hint-box',
    name: 'HintBox 工具',
    hotkey: 'B',
    icon: <BsQuestionSquare size={24} />,
    editorTool: 'rect',
    createDefinition: (annotation: Annotation): HintBoxDefinition => {
        if (annotation.type !== 'rect') {
            throw new Error('HintBox tool must be used with a rect annotation');
        }
        return {
            name: `hintbox_${annotation.id.substring(0, 4)}`,
            displayName: '',
            description: '',
            type: 'hint-box',
            annotationId: annotation.id,
        };
    },
    // PropertiesComponent will be implemented in a later task
};

export default hintBoxTool;
