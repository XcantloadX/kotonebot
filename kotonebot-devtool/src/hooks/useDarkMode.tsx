import { useState, useEffect } from 'react';

export type ThemeMode = 'dark' | 'light' | 'system';

interface UseDarkModeOptions<T> {
    whenDark: T;
    whenLight: T;
}

interface UseDarkModeResult<T> {
    theme: T;
    isDark: boolean;
    themeMode: ThemeMode;
    setThemeMode: (mode: ThemeMode) => void;
    toggleTheme: () => void;
}

export function useDarkMode<T>(options: UseDarkModeOptions<T>): UseDarkModeResult<T> {
    const { whenDark: darkTheme, whenLight: lightTheme } = options;

    const [themeMode, setThemeMode] = useState<ThemeMode>('system');
    const [systemIsDark, setSystemIsDark] = useState(() => 
        window.matchMedia('(prefers-color-scheme: dark)').matches
    );

    // 切换主题
    const toggleTheme = () => {
        setThemeMode(themeMode === 'dark' ? 'light' : 'dark');
    };

    // 监听系统主题变化
    useEffect(() => {
        const darkModeMediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
        
        const handleThemeChange = (e: MediaQueryListEvent | MediaQueryList) => {
            setSystemIsDark(e.matches);
        };

        handleThemeChange(darkModeMediaQuery);
        darkModeMediaQuery.addEventListener('change', handleThemeChange);

        return () => {
            darkModeMediaQuery.removeEventListener('change', handleThemeChange);
        };
    }, []);

    // 根据当前模式和系统主题计算实际的主题状态
    const isDark = themeMode === 'system' ? systemIsDark : themeMode === 'dark';
    const theme = isDark ? darkTheme : lightTheme;

    return {
        theme,
        isDark,
        themeMode,
        setThemeMode,
        toggleTheme,
    };
}
