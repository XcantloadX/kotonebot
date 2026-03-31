import { EditorApp } from './editor/EditorApp';
import { MessageBoxProvider } from './ui/messageBox';
import { ShortcutProvider } from './shortcuts/shortcutManager';
import { QuickPickProvider } from './ui/quickPick';
import { ProjectInfoBootstrapper } from './app/ProjectInfoBootstrapper';

function App() {
  return (
    <div className="">
      <ShortcutProvider>
        <QuickPickProvider>
          <MessageBoxProvider>
            <ProjectInfoBootstrapper />
            <EditorApp />
          </MessageBoxProvider>
        </QuickPickProvider>
      </ShortcutProvider>
    </div>
  )
}

export default App
