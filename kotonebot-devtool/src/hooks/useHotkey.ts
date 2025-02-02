import { useCallback, useEffect } from 'react';

export interface HotkeyConfig {
    key: string;
    ctrl?: boolean;
    shift?: boolean;
    alt?: boolean;
    /** 是否是单按键（不需要修饰键） */
    single?: boolean;
    /** 是否在输入框中也触发 */
    triggerInInput?: boolean;
    callback: () => void;
}

/**
 * 热键 Hook
 * @param hotkeys 热键配置数组
 * @example
 * ```tsx
 * // 使用示例
 * useHotkey([
 *   // Ctrl + S
 *   { key: 's', ctrl: true, callback: handleSave },
 *   // 单按 V 键
 *   { key: 'v', single: true, callback: () => setTool('select') },
 * ]);
 * ```
 */
const useHotkey = (hotkeys: HotkeyConfig[]) => {
    const handleKeyDown = useCallback((e: KeyboardEvent) => {
        // 获取当前按键的小写形式
        const key = e.key.toLowerCase();

        // 检查是否在输入框中
        const isInInput = e.target instanceof HTMLInputElement || 
                         e.target instanceof HTMLTextAreaElement;

        // 遍历所有热键配置
        for (const hotkey of hotkeys) {
            // 如果在输入框中且不允许在输入框触发，则跳过
            if (isInInput && !hotkey.triggerInInput) {
                continue;
            }

            // 检查按键是否匹配
            if (key !== hotkey.key.toLowerCase()) {
                continue;
            }

            // 对于单按键，检查是否有修饰键被按下
            if (hotkey.single) {
                if (e.ctrlKey || e.shiftKey || e.altKey) {
                    continue;
                }
                hotkey.callback();
                return;
            }

            // 对于组合键，检查修饰键是否匹配
            if (e.ctrlKey === !!hotkey.ctrl &&
                e.shiftKey === !!hotkey.shift &&
                e.altKey === !!hotkey.alt) {
                e.preventDefault(); // 阻止默认行为
                hotkey.callback();
                return;
            }
        }
    }, [hotkeys]);

    useEffect(() => {
        document.addEventListener('keydown', handleKeyDown);
        return () => {
            document.removeEventListener('keydown', handleKeyDown);
        };
    }, [handleKeyDown]);
};

export default useHotkey;
