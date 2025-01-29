import { create } from 'zustand';
import { KotoneDebugClient } from '../utils/debugClient';

interface DebugState {
  client: KotoneDebugClient | null;
  host: string;
}

export const useDebugStore = create<DebugState>(() => ({
  client: null,
  host: '127.0.0.1:8000',
}));
  
export function useDebugClient() {
  const client = useDebugStore(state => state.client);
  const host = useDebugStore(state => state.host);
  if (!client) {
    const _client = new KotoneDebugClient(host);
    useDebugStore.setState({ client: _client });
    return _client;
  }
  return client;
}
