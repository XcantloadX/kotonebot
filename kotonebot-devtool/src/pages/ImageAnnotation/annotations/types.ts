import React from 'react';
import { Annotation } from '../../../components/ImageEditor/types';
import { Definition } from '../types/definitions';

/**
 * Represents a complete annotation instance, combining the geometric
 * annotation data with its semantic definition.
 */
export interface AnnotationInstance {
    annotation: Annotation;
    definition: Definition;
}

/**
 * Props for a component that renders the properties of an annotation instance.
 */
export interface AnnotationInstancePropertiesProps {
    instance: AnnotationInstance;
    onInstanceChange: (defChanges: Partial<Definition>, annChanges: Partial<Annotation>) => void;
}

/**
 * Defines a plugin for a specific type of annotation (e.g., 'rect', 'point').
 * This plugin provides the UI for editing the common properties of that annotation type.
 */
export interface AnnotationTypePlugin {
    /**
     * The type of annotation this plugin handles (e.g., 'rect', 'point').
     */
    type: Annotation['type'];

    /**
     * A React component for rendering the common properties of this annotation type.
     * This is used to build the dynamic property panel.
     */
    PropertiesComponent: React.FC<AnnotationInstancePropertiesProps>;
}
