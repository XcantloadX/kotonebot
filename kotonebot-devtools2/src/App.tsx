import { EditorApp } from './editor/EditorApp';
import { MessageBoxProvider } from './ui/messageBox';
import { ShortcutProvider } from './shortcuts/shortcutManager';
import { QuickPickProvider } from './ui/quickPick';

function App() {
  return (
    <div className="">
      <ShortcutProvider>
        <QuickPickProvider>
          <MessageBoxProvider>
            <EditorApp />
          </MessageBoxProvider>
        </QuickPickProvider>
      </ShortcutProvider>
    </div>
  )
}

export default App
