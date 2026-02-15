import { EditorApp } from './editor/EditorApp';
import { MessageBoxProvider } from './ui/messageBox';

function App() {
  return (
    <div className="">
      <MessageBoxProvider>
        <EditorApp />
      </MessageBoxProvider>
    </div>
  )
}

export default App
