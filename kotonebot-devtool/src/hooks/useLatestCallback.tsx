import { useRef } from "react";

import { useCallback } from "react";

// https://github.com/facebook/react/issues/14099
function useLatestCallback<T extends (...args: any[]) => any>(callback: T): T {
    const ref = useRef(callback);
    const latest = useCallback((...args: Parameters<T>) => {
        return ref.current(...args);
    }, []);
    ref.current = callback;
    return latest as T;
}

export default useLatestCallback;