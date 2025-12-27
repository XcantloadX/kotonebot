import { useEffect, useRef } from 'react';

export type KeyHandler = (e: KeyboardEvent) => void;

export interface ShortcutHandlers {
    onKeyDown?: KeyHandler;
    onKeyUp?: KeyHandler;
}

export interface ShortcutMap {
    [key: string]: ShortcutHandlers;
}

/**
 * Hook for handling global keyboard shortcuts centrally.
 * Registers only one pair of listeners for the window.
 * 
 * @param map Object mapping keys (e.code or e.key) to handlers.
 */
export const useShortcuts = (map: ShortcutMap) => {
    const mapRef = useRef(map);
    
    // Update ref on every render so handlers capture latest state
    useEffect(() => {
        mapRef.current = map;
    });

    useEffect(() => {
        const handleKeyDown = (e: KeyboardEvent) => {
            // Check against both code and key
            const handlers = mapRef.current[e.code] || mapRef.current[e.key];
            if (handlers?.onKeyDown) {
                handlers.onKeyDown(e);
            }
        };

        const handleKeyUp = (e: KeyboardEvent) => {
            const handlers = mapRef.current[e.code] || mapRef.current[e.key];
            if (handlers?.onKeyUp) {
                handlers.onKeyUp(e);
            }
        };

        window.addEventListener('keydown', handleKeyDown);
        window.addEventListener('keyup', handleKeyUp);

        return () => {
            window.removeEventListener('keydown', handleKeyDown);
            window.removeEventListener('keyup', handleKeyUp);
        };
    }, []); // Empty dependency array: listeners are registered only once
};
