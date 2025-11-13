import { AnnotationTypePlugin } from './types';

/**
 * A registry for managing annotation type plugins.
 * This allows for dynamic registration and retrieval of annotation property editors.
 */
class AnnotationRegistry {
    private plugins: Map<string, AnnotationTypePlugin> = new Map();

    /**
     * Registers a new annotation type plugin.
     * If a plugin for the same type is already registered, it will be overwritten.
     * @param plugin The annotation type plugin to register.
     */
    register(plugin: AnnotationTypePlugin) {
        if (this.plugins.has(plugin.type)) {
            console.warn(`Annotation type plugin for type '${plugin.type}' is already registered. Overwriting.`);
        }
        this.plugins.set(plugin.type, plugin);
    }

    /**
     * Retrieves an annotation type plugin by its type.
     * @param type The type of the annotation plugin to retrieve (e.g., 'rect', 'point').
     * @returns The annotation type plugin, or undefined if not found.
     */
    get(type: string): AnnotationTypePlugin | undefined {
        return this.plugins.get(type);
    }

    /**
     * Retrieves all registered annotation type plugins.
     * @returns An array of all annotation type plugins.
     */
    getAll(): AnnotationTypePlugin[] {
        return Array.from(this.plugins.values());
    }
}

/**
 * Singleton instance of the AnnotationRegistry.
 */
export const annotationRegistry = new AnnotationRegistry();
