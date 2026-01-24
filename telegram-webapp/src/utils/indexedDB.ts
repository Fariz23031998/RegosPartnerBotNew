const DB_NAME = 'DataDB';
const DB_VERSION = 1; 
const SETTINGS_STORE = 'settings';

class IndexedDBService {
    private db: IDBDatabase | null = null;
    private initPromise: Promise<void> | null = null;

    async init(): Promise<void> {
        // Return existing initialization if in progress
        if (this.initPromise) {
            return this.initPromise;
        }

        // Return immediately if already initialized
        if (this.db) {
            return Promise.resolve();
        }

        this.initPromise = new Promise((resolve, reject) => {
            const request = indexedDB.open(DB_NAME, DB_VERSION);

            request.onerror = () => {
                this.initPromise = null;
                reject(request.error);
            };

            request.onsuccess = () => {
                this.db = request.result;
                this.initPromise = null;
                console.log('IndexedDB initialized successfully');
                resolve();
            };

            request.onupgradeneeded = (event) => {
                const db = (event.target as IDBOpenDBRequest).result;
                const oldVersion = event.oldVersion;

                console.log(`Upgrading database from version ${oldVersion} to ${DB_VERSION}`);


                if (!db.objectStoreNames.contains(SETTINGS_STORE)) {
                    db.createObjectStore(SETTINGS_STORE, { keyPath: 'key' });
                    console.log('Created settings store');
                }

                console.log('Database upgrade completed');
            };
        });

        return this.initPromise;
    }

    async saveSetting(key: string, value: any): Promise<void> {
        if (!this.db) await this.init();

        return new Promise((resolve, reject) => {
            const transaction = this.db!.transaction([SETTINGS_STORE], 'readwrite');
            const store = transaction.objectStore(SETTINGS_STORE);

            store.put({ key, value });

            transaction.oncomplete = () => resolve();
            transaction.onerror = () => reject(transaction.error);
        });
    }

    async getSetting(key: string): Promise<any> {
        if (!this.db) await this.init();

        return new Promise((resolve, reject) => {
            const transaction = this.db!.transaction([SETTINGS_STORE], 'readonly');
            const store = transaction.objectStore(SETTINGS_STORE);
            const request = store.get(key);

            request.onsuccess = () => resolve(request.result?.value);
            request.onerror = () => reject(request.error);
        });
    }

    async saveLanguage(langCode: string, version: string, translations: any): Promise<void> {
        if (!this.db) await this.init();

        return new Promise((resolve, reject) => {
            const transaction = this.db!.transaction([SETTINGS_STORE], 'readwrite');
            const store = transaction.objectStore(SETTINGS_STORE);

            store.put({ key: `lang_${langCode}`, value: translations });
            store.put({ key: `lang_${langCode}_version`, value: version });

            transaction.oncomplete = () => resolve();
            transaction.onerror = () => reject(transaction.error);
        });
    }

    async getLanguage(langCode: string): Promise<any | null> {
        if (!this.db) await this.init();

        return new Promise((resolve, reject) => {
            const transaction = this.db!.transaction([SETTINGS_STORE], 'readonly');
            const store = transaction.objectStore(SETTINGS_STORE);
            const request = store.get(`lang_${langCode}`);

            request.onsuccess = () => resolve(request.result?.value || null);
            request.onerror = () => reject(request.error);
        });
    }

    async getLanguageVersion(langCode: string): Promise<string | null> {
        if (!this.db) await this.init();

        return new Promise((resolve, reject) => {
            const transaction = this.db!.transaction([SETTINGS_STORE], 'readonly');
            const store = transaction.objectStore(SETTINGS_STORE);
            const request = store.get(`lang_${langCode}_version`);

            request.onsuccess = () => resolve(request.result?.value || null);
            request.onerror = () => reject(request.error);
        });
    }

    async clearLanguageData(): Promise<void> {
        if (!this.db) await this.init();

        return new Promise((resolve, reject) => {
            const transaction = this.db!.transaction([SETTINGS_STORE], 'readwrite');
            const store = transaction.objectStore(SETTINGS_STORE);
            const request = store.getAllKeys();

            request.onsuccess = () => {
                const keys = request.result;
                const deleteRequests: IDBRequest[] = [];

                for (const key of keys) {
                    if (typeof key === 'string' && key.startsWith('lang_')) {
                        deleteRequests.push(store.delete(key));
                    }
                }

                if (deleteRequests.length === 0) {
                    resolve();
                    return;
                }

                let completed = 0;
                deleteRequests.forEach(req => {
                    req.onsuccess = () => {
                        completed++;
                        if (completed === deleteRequests.length) resolve();
                    };
                    req.onerror = () => reject(req.error);
                });
            };
            request.onerror = () => reject(request.error);
        });
    }
}


export const indexedDBService = new IndexedDBService();