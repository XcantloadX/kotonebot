import { ErrorBoundary } from './ui/ErrorBoundary';
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
    <ErrorBoundary>
      <div className="">
        <ShortcutProvider>
          <QuickPickProvider>
            <MessageBoxProvider>
              <EditorApp />
            </MessageBoxProvider>
          </QuickPickProvider>
        </ShortcutProvider>
      </div>
    </ErrorBoundary>
  )
}

export default App
