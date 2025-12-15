import { toolRegistry } from '../registry';
import templateTool from './templateTool.tsx';
import hintBoxTool from './hintBoxTool.tsx';
import hintPointTool from './hintPointTool.tsx';

/**
 * Registers all the available tool plugins.
 * This function should be called once when the application initializes.
 */
export function registerToolPlugins() {
    toolRegistry.register(templateTool);
    toolRegistry.register(hintBoxTool);
    toolRegistry.register(hintPointTool);
}
