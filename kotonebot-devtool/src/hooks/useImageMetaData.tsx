import { Annotation } from "../components/ImageEditor/types";
import { useImmer } from "use-immer";
import { DefinitionType, BaseDefinition, TemplateDefinition, HintBoxDefinition, HintPointDefinition, Definition, Definitions, ImageMetaData } from "../pages/ImageAnnotation/types/definitions";

export type { DefinitionType, BaseDefinition, TemplateDefinition, HintBoxDefinition, HintPointDefinition, Definition, Definitions, ImageMetaData };

function fromString(data: string): ImageMetaData {
    return JSON.parse(data);
}

function toString(data: ImageMetaData): string {
    const replacer = (key: string, value: any) => {
        if (key.startsWith('_')) {
            return undefined;
        }
        return value;
    };
    return JSON.stringify(data, replacer);
}


function useImageMetaData(data?: ImageMetaData) {
    const [imageMetaData, updateImageMetaData] = useImmer<ImageMetaData>(data || {
        definitions: {},
        annotations: [],
    });

    const Definitions = {
        get: (annotationId: string) => {
            return imageMetaData.definitions[annotationId];
        },
        add: (definition: Definition) => {
            updateImageMetaData(draft => {
                draft.definitions[definition.annotationId] = definition;
            });
        },
        update: (definition: Partial<Definition> & { annotationId: string }) => {
            updateImageMetaData(draft => {
                Object.assign(draft.definitions[definition.annotationId], definition);
            });
        },
        remove: (annotationId: string) => {
            updateImageMetaData(draft => {
                delete draft.definitions[annotationId];
            });
        },
    };

    const Annotations = {
        get: (id: string) => {
            return imageMetaData.annotations.find(a => a.id === id);
        },
        add: (annotation: Annotation) => {
            updateImageMetaData(draft => {
                draft.annotations.push(annotation);

            });
        },
        update: (annotation: Partial<Annotation> & { id: string }) => {
            updateImageMetaData(draft => {
                const oldAnnotation = draft.annotations.find(a => a.id === annotation.id);
                if (oldAnnotation) {
                    Object.assign(oldAnnotation, annotation);
                }
            });
        },
        remove: (id: string) => {
            updateImageMetaData(draft => {
                draft.annotations = draft.annotations.filter(a => a.id !== id);
            });
        },
    };

    const clear = () => {
        updateImageMetaData(draft => {
            draft.definitions = {};
            draft.annotations = [];
        });
    };

    const load = (data: Partial<ImageMetaData>) => {
        updateImageMetaData(draft => {
            if (data.definitions) {
                draft.definitions = { ...data.definitions };
            }
            if (data.annotations) {
                draft.annotations = [...data.annotations];
            }
        });
    };

    return {
        imageMetaData,
        /** 对图像定义数据的操作对象 */
        Definitions,
        /** 对图像标注数据的操作对象 */
        Annotations,
        /** 清空图像元数据 */
        clear,
        /** 载入图像元数据 */
        load,
        /** 检查是否没有任何标注和定义 */
        isEmpty: () => imageMetaData.annotations.length === 0 && Object.keys(imageMetaData.definitions).length === 0,
        /** 将图像元数据转换为字符串 */
        toString,
        /** 将字符串转换为图像元数据 */
        fromString,
    };
}


export default useImageMetaData;