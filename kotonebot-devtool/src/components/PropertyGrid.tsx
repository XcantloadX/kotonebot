import styled from '@emotion/styled';
import React, { useState, useRef } from 'react';

export interface PropertyRenderBase {
  required?: boolean,
}

interface PropertyRenderInputOptions {
  text: {
    value: string,
    onChange: (value: string) => void
  },
  checkbox: {
    value: boolean,
    onChange: (value: boolean) => void
  }
}
type RenderType = keyof PropertyRenderInputOptions;

type PropertyRender = 
  (PropertyRenderBase & PropertyRenderInputOptions[RenderType] & { type: RenderType }) |
  (() => React.ReactNode);

/** 
 * 表示一个属性项的配置
 * @property title - 可选的属性标题。如果不提供,属性将占据整行显示
 * @property render - 渲染属性内容的函数。返回的内容将显示在属性值区域
 */
export interface Property {
  title?: string;
  render: PropertyRender;
}

/**
 * 表示一个属性分类的配置
 * @property title - 分类的标题
 * @property properties - 该分类下的属性数组
 * @property foldable - 是否可以折叠。如果为 true,分类标题将显示折叠按钮
 */
export interface PropertyCategory {
  title: string;
  properties: Property[];
  foldable?: boolean;
}

export interface PropertyGridProps {
  properties: Array<Property | PropertyCategory>;
  titleColumnWidth?: string;
}

const GridContainer = styled.div<{ titleColumnWidth: string }>`
  display: grid;
  grid-template-columns: ${props => props.titleColumnWidth} 1fr;
  gap: 1px;
  background-color: #e0e0e0;
  border: 1px solid #e0e0e0;
`;

const PropertyTitle = styled.div`
  padding: 8px;
  background-color: #f5f5f5;
  font-size: 14px;
  display: flex;
  align-items: center;
`;

const PropertyContent = styled.div`
  padding: 4px 8px;
  background-color: white;
  min-height: 32px;
  display: flex;
  align-items: center;
`;

const FullWidthPropertyContent = styled(PropertyContent)`
  grid-column: 1 / -1;
`;

const CategoryTitle = styled.div<{ foldable?: boolean }>`
  grid-column: 1 / -1;
  padding: 8px;
  background-color: #edf2f7;
  font-weight: 600;
  font-size: 14px;
  color: #2d3748;
  border-bottom: 1px solid #e0e0e0;
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: ${props => props.foldable ? 'pointer' : 'default'};

  &:hover {
    background-color: ${props => props.foldable ? '#e2e8f0' : '#edf2f7'};
  }
`;

const FoldIcon = styled.span<{ folded: boolean }>`
  width: 20px;
  height: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: transform 0.2s;
  transform: rotate(${props => props.folded ? '-90deg' : '0deg'});
  flex-shrink: 0;
  
  &::before {
    content: '▼';
    font-size: 12px;
  }
`;

const CategoryContent = styled.div<{ folded: boolean }>`
  display: grid;
  grid-template-columns: subgrid;
  grid-column: 1 / -1;
  display: ${props => props.folded ? 'none' : 'grid'};
`;

const PropertyGrid: React.FC<PropertyGridProps> = ({ properties, titleColumnWidth = 'auto' }) => {
  const [foldedCategories, setFoldedCategories] = useState<Record<string, boolean>>({});

  const toggleCategory = (categoryTitle: string) => {
    setFoldedCategories(prev => ({
      ...prev,
      [categoryTitle]: !prev[categoryTitle]
    }));
  };

  /**
   * 渲染单个属性项
   * @param property - 属性配置
   */
  const makeProperty = (property: Property) => {
    let field: React.ReactNode;
    if (typeof property.render === 'function') {
      field = property.render();
    } else if ('type' in property.render) {
      const type = property.render.type;
      if (type === 'text') {
        const propertyText = property.render as PropertyRenderInputOptions['text'];
        field = <input type="text" value={propertyText.value} onChange={(e) => propertyText.onChange(e.target.value)} />;
      } else if (type === 'checkbox') {
        const propertyCheckbox = property.render as PropertyRenderInputOptions['checkbox'];
        field = <input type="checkbox" checked={propertyCheckbox.value} onChange={(e) => propertyCheckbox.onChange(e.target.checked)} />;
      }
    } else {
      console.error('Invalid property render type:', property.render);
    }
    if (property.title) {
      return (
        <>
          <PropertyTitle>{property.title}</PropertyTitle>
          <PropertyContent>{field}</PropertyContent>
        </>
      );
    }
    return <FullWidthPropertyContent>{field}</FullWidthPropertyContent>;
  };

  /**
   * 渲染属性分类
   * @param category - 分类配置
   * @param index - 分类索引
   */
  const makeCategory = (category: PropertyCategory, index: number) => {
    return (
      <>
        <CategoryTitle 
          foldable={category.foldable}
          onClick={() => category.foldable && toggleCategory(category.title)}
        >
          {category.foldable && (
            <FoldIcon folded={foldedCategories[category.title]} />
          )}
          <span>{category.title}</span>
        </CategoryTitle>
        <CategoryContent 
          folded={category.foldable ? !!foldedCategories[category.title] : false}
        >
          {category.properties.map((subProperty, subIndex) => (
            <React.Fragment key={`${index}-${subIndex}`}>
              {makeProperty(subProperty)}
            </React.Fragment>
          ))}
        </CategoryContent>
      </>
    );
  };

  return (
    <GridContainer titleColumnWidth={titleColumnWidth}>
      {properties.map((property, index) => (
        <React.Fragment key={index}>
          {'properties' in property 
            ? makeCategory(property, index)
            : makeProperty(property)
          }
        </React.Fragment>
      ))}
    </GridContainer>
  );
};

export default PropertyGrid;
