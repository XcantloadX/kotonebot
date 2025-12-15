import React from 'react';
import { Tool as EditorTool, Annotation } from '../../../components/ImageEditor/types';
import { Definition } from '../types/definitions';

/**
 * Represents a tool plugin in the image annotation system.
 * Each tool plugin defines a specific type of annotation or interaction.
 */
export interface ToolPlugin {
    /**
     * Unique identifier for the tool (e.g., 'template', 'hint-box').
     * This should match the 'type' in the corresponding Definition.
     */
    id: string;
    
    /**
     * The name of the tool to be displayed in the UI, such as in tooltips.
     */
    name: string;

    /**
     * The keyboard shortcut for activating the tool.
     */
    hotkey?: string;

    /**
     * The icon for the tool to be displayed in the toolbar.
     */
    icon: React.ReactNode;

    /**
     * The underlying editor tool that this plugin uses (e.g., 'rect', 'point').
     */
    editorTool: EditorTool;

    /**
     * A function that creates a new Definition object when an annotation is created
     * using this tool.
     * @param annotation The newly created annotation.
     * @returns A new Definition object associated with the annotation.
     */
    createDefinition: (annotation: Annotation) => Definition;

    /**
     * An optional React component for rendering the specific properties of a
     * definition associated with this tool. This will be displayed in the property panel.
     */
    PropertiesComponent?: React.FC<{ definition: Definition, onUpdate: (changes: Partial<Definition>) => void }>;
}
