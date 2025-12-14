import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

const webComponentImport = {
  name: 'web-component-import',
  transform(code: string, id: string) {
    if (id.endsWith('.component.html')) {
      const retCodes: string[] = [];
      retCodes.push('loadComponent(');
      code.split('\n').forEach(line => {
        line = line.trimEnd();
        line = line.replaceAll('"', '\\"');
        line = '"' + line + '\\n" +';
        retCodes.push(line);
      });
      retCodes.push('""')
      retCodes.push(');');
      // console.log(retCodes.join('\n'));
      return retCodes.join('\n');
    } else {
      return code;
    }
  }
}

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    react({ jsxImportSource: '@emotion/react' }),
    webComponentImport
  ],
  
})
