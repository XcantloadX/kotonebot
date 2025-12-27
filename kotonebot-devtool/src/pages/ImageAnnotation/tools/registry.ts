import { ToolPlugin } from './types';

/**
 * A registry for managing tool plugins.
 * This allows for dynamic registration and retrieval of tools.
 */
class ToolRegistry {
    private plugins: Map<string, ToolPlugin> = new Map();

    /**
     * Registers a new tool plugin.
     * If a plugin with the same ID is already registered, it will be overwritten.
     * @param plugin The tool plugin to register.
     */
    register(plugin: ToolPlugin) {
        if (this.plugins.has(plugin.id)) {
            console.warn(`Tool plugin with id '${plugin.id}' is already registered. Overwriting.`);
        }
        this.plugins.set(plugin.id, plugin);
    }

    /**
     * Retrieves a tool plugin by its ID.
     * @param id The ID of the tool plugin to retrieve.
     * @returns The tool plugin, or undefined if not found.
     */
    get(id: string): ToolPlugin | undefined {
        return this.plugins.get(id);
    }

    /**
     * Retrieves all registered tool plugins.
     * @returns An array of all tool plugins.
     */
    getAll(): ToolPlugin[] {
        return Array.from(this.plugins.values());
    }
}

/**
 * Singleton instance of the ToolRegistry.
 */
export const toolRegistry = new ToolRegistry();
