import { useShortcut } from '../shortcuts/shortcutManager';
import { useEditorDialogsContext } from './EditorDialogsContext';
import { COMMAND_ID, executeCommand } from './commands';

export function EditorShortcuts() {
  const { commandContext } = useEditorDialogsContext();

  useShortcut({
    id: 'editor.open-command-palette',
    combo: 'mod+shift+p',
    scope: 'editor',
    onKeyDown: () => executeCommand(COMMAND_ID.APP_OPEN_COMMAND_PALETTE, commandContext, undefined),
  });

  useShortcut({
    id: 'editor.toggle-problems-panel',
    combo: 'mod+shift+m',
    scope: 'editor',
    onKeyDown: () => executeCommand(COMMAND_ID.APP_TOGGLE_PROBLEMS_PANEL, commandContext, undefined),
  });

  return null;
}
