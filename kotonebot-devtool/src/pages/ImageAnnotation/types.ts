import { Annotation } from '../../components/ImageEditor/types';

export type DefinitionType = 'template' | 'ocr' | 'color';

export interface BaseDefinition {
    /** 最终出现在 R.py 中的名称 */
    name: string;
    /** 显示在调试器与调试输出中的名称 */
    displayName: string;
    type: DefinitionType;
    /** 标注 ID */
    annotationId: string;
}


export interface TemplateDefinition extends BaseDefinition {
    type: 'template';
    /**
     * 是否将这个模板的矩形范围作为运行时
     * 执行模板寻找函数时的提示范围。
     * 
     * 若为 true，则运行时会先在这个范围内寻找，
     * 如果没找到，再在整张截图中寻找。
     */
    useHintRect: boolean
}


export type Definitions = Record<string, BaseDefinition>;

export interface ImageMetaData {
    definitions: Definitions;
    annotations: Annotation[];
}