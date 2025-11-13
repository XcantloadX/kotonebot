import React from 'react';
import { Annotation } from '../../../components/ImageEditor/types';
import { Definitions, Definition } from '../types/definitions';
import { FileResult, cropImage } from '../../../utils/fileUtils';
import { Property, PropertyCategory } from '../../../components/PropertyGrid';

export function usePropertyGridData(
    selectedAnnotation: Annotation | null,
    definitions: Definitions,
    image: HTMLImageElement | null,
    onImageClick: (imageUrl: string) => void,
    onDefinitionChange?: (id: string, changes: Partial<Definition>) => void,
    imageFileName?: string,
    annotations?: Annotation[],
    currentFileResult?: FileResult | null
) {
    const [croppedImageUrl, setCroppedImageUrl] = React.useState<string>('');

    React.useEffect(() => {
        if (selectedAnnotation && selectedAnnotation.type === 'rect' && image) {
            const url = cropImage(image, selectedAnnotation.data);
            setCroppedImageUrl(url);
        } else {
            setCroppedImageUrl('');
        }
    }, [selectedAnnotation, image]);

    if (!selectedAnnotation) {
        if (!image) return [];
        const gcd = (a: number, b: number): number => {
            a = Math.abs(a);
            b = Math.abs(b);
            while (b) {
                const t = b;
                b = a % b;
                a = t;
            }
            return a;
        };
        const getSimplestRatio = (width: number, height: number): string => {
            const divisor = gcd(width, height);
            return `${width / divisor}:${height / divisor}`;
        };

        return [
            { title: '文件名', render: () => imageFileName || '未命名' },
            { title: '标注文件', render: () => currentFileResult?.name || '空' },
            { title: '打开方式', render: () => currentFileResult?.fileSystem === 'wfs' ? 'WebFileSystem' : 'Input' },
            { title: '宽高', render: () => `${image.width} × ${image.height}` },
            { title: '宽高比', render: () => getSimplestRatio(image.width, image.height) },
            { title: '标注数量', render: () => annotations?.length || 0 }
        ];
    }

    const definition = definitions[selectedAnnotation.id];
    if (!definition) return [];

    const generalProperties: Array<PropertyCategory | Property> = [
        {
            render: () => {
                if (!image || !croppedImageUrl) return null;
                return (
                    <div style={{ height: '100px', margin: '0 auto' }}>
                        <img
                            src={croppedImageUrl}
                            style={{ maxWidth: '100%', maxHeight: '100px', objectFit: 'contain', cursor: 'pointer' }}
                            onClick={() => onImageClick(croppedImageUrl)}
                        />
                    </div>
                );
            },
        },
        {
            title: '通用',
            properties: [
                { title: '名称', render: { type: 'text', required: true, value: definition.name, onChange: (value: string) => onDefinitionChange?.(selectedAnnotation.id, { name: value }) } },
                { title: '显示名称', render: { type: 'text', required: true, value: definition.displayName, onChange: (value: string) => onDefinitionChange?.(selectedAnnotation.id, { displayName: value }) } },
                { title: '描述', render: { type: 'long-text', value: definition.description || '', onChange: (value: string) => onDefinitionChange?.(selectedAnnotation.id, { description: value }) } },
                {
                    title: '类型',
                    render: {
                        type: 'select',
                        required: true,
                        value: definition.type,
                        options: selectedAnnotation.type === 'rect'
                            ? [{ value: 'template', label: '模板' }, { value: 'hint-box', label: 'HintBox' }]
                            : [{ value: 'hint-point', label: 'HintPoint' }],
                        onChange: (value) => onDefinitionChange?.(selectedAnnotation.id, { type: value as any }),
                    }
                }
            ],
            foldable: true
        },
    ];

    let annotationProperties: Array<PropertyCategory | Property> = [];
    if (selectedAnnotation.type === 'rect') {
        const { x1, y1, x2, y2 } = selectedAnnotation.data;
        annotationProperties = [{ title: '标注', properties: [
            { title: 'ID', render: () => selectedAnnotation.id },
            { title: '类型', render: () => '矩形' },
            { title: '范围', render: () => `(${x1}, ${y1}, ${x2}, ${y2})` },
            { title: '宽高', render: () => `${x2 - x1} × ${y2 - y1}` }
        ], foldable: true }];
    } else if (selectedAnnotation.type === 'point') {
        const { x, y } = selectedAnnotation.data;
        annotationProperties = [{ title: '标注', properties: [
            { title: 'ID', render: () => selectedAnnotation.id },
            { title: '类型', render: () => '点' },
            { title: '位置', render: () => `(${x}, ${y})` }
        ], foldable: true }];
    }

    return [...generalProperties, ...annotationProperties];
}
