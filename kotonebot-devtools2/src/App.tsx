import { EditorApp } from './editor/EditorApp';
import { MessageBoxProvider } from './ui/messageBox';
import { ShortcutProvider } from './shortcuts/shortcutManager';
import { QuickPickProvider } from './ui/quickPick';
import { useProjectInfoReady } from './app/ProjectInfoBootstrapper';

function App() {
  const isReady = useProjectInfoReady();

  if (!isReady) {
    return null;
  }

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
