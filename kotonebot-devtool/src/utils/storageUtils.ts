interface ScriptRecorderData {
    code: string;
    directoryHandle?: FileSystemDirectoryHandle;
}

interface StorageData {
    last: ScriptRecorderData;
}

export class ScriptRecorderStorage {
    private static readonly STORAGE_KEY = 'scriptRecorder';
    private static readonly DB_NAME = 'scriptRecorderDB';
    private static readonly STORE_NAME = 'fileHandles';
    private static readonly DB_VERSION = 1;

    static saveCode(code: string): void {
        const data: StorageData = {
            last: { code }
        };
        localStorage.setItem(this.STORAGE_KEY, JSON.stringify(data));
    }

    static loadCode(): string | null {
        const dataStr = localStorage.getItem(this.STORAGE_KEY);
        if (!dataStr) return null;

        try {
            const data = JSON.parse(dataStr) as StorageData;
            return data.last.code;
        } catch (e) {
            console.error('Failed to parse script recorder data:', e);
            return null;
        }
    }

    static clearCode(): void {
        localStorage.removeItem(this.STORAGE_KEY);
    }

    private static async getDB(): Promise<IDBDatabase> {
        return new Promise((resolve, reject) => {
            const request = indexedDB.open(this.DB_NAME, this.DB_VERSION);

            request.onerror = () => reject(request.error);
            request.onsuccess = () => resolve(request.result);

            request.onupgradeneeded = (event) => {
                const db = (event.target as IDBOpenDBRequest).result;
                if (!db.objectStoreNames.contains(this.STORE_NAME)) {
                    db.createObjectStore(this.STORE_NAME);
                }
            };
        });
    }

    static async saveDirectoryHandle(handle: FileSystemDirectoryHandle): Promise<void> {
        const db = await this.getDB();
        return new Promise((resolve, reject) => {
            const transaction = db.transaction(this.STORE_NAME, 'readwrite');
            const store = transaction.objectStore(this.STORE_NAME);
            const request = store.put(handle, 'directoryHandle');

            request.onerror = () => reject(request.error);
            request.onsuccess = () => resolve();
        });
    }

    static async loadDirectoryHandle(): Promise<FileSystemDirectoryHandle | null> {
        const db = await this.getDB();
        return new Promise((resolve, reject) => {
            const transaction = db.transaction(this.STORE_NAME, 'readonly');
            const store = transaction.objectStore(this.STORE_NAME);
            const request = store.get('directoryHandle');

            request.onerror = () => reject(request.error);
            request.onsuccess = () => resolve(request.result || null);
        });
    }

    static async verifyDirectoryHandlePermission(handle: FileSystemDirectoryHandle): Promise<boolean> {
        try {
            const options = { mode: 'readwrite' } as const;
            // @ts-ignore
            const permission = await handle.requestPermission(options);
            return permission === 'granted';
        } catch (e) {
            console.error('Failed to verify directory handle permission:', e);
            return false;
        }
    }
}
