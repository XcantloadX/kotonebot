import { EditorApp } from './editor/EditorApp';
import { MessageBoxProvider } from './ui/messageBox';
import { ShortcutProvider } from './shortcuts/shortcutManager';

function App() {
  return (
    <div className="">
      <ShortcutProvider>
        <MessageBoxProvider>
          <EditorApp />
        </MessageBoxProvider>
      </ShortcutProvider>
    </div>
  )
}

export default App
