import { Annotation } from "../../../components/ImageEditor/types";

export type DefinitionType = 'template' | 'ocr' | 'color' | 'hint-box' | 'hint-point';

export interface BaseDefinition {
    /** 最终出现在 R.py 中的名称 */
    name: string;
    /** 显示在调试器与调试输出中的名称 */
    displayName: string;
    /** 描述信息 */
    description: string;
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
    fixed: boolean
    /**
     * 模板匹配阈值，null 表示使用默认值
     */
    threshold: number | null
    /**
     * 是否启用颜色识别，null 表示使用默认设置
     */
    colored: boolean | null
}

export interface HintBoxDefinition extends BaseDefinition {
    type: 'hint-box';
}

export interface HintPointDefinition extends BaseDefinition {
    type: 'hint-point';
}

export type Definition = TemplateDefinition | HintBoxDefinition | HintPointDefinition;

export type Definitions = Record<string, Definition>;

export interface ImageMetaData {
    definitions: Definitions;
    annotations: Annotation[];
}
