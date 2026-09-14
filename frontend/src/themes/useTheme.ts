import { useState, useEffect, useCallback } from 'react';

const STORAGE_KEY = 'ai-platform.palette';
const THEMES = ['deep-space', 'mahogany', 'monochrome', 'coffee'] as const;
const LABELS = ['Deep Space', 'Mahogany', 'Monochrome', 'Coffee'];

type ThemeKey = (typeof THEMES)[number];

export function useTheme() {
  const [index, setIndex] = useState<number>(() => {
    const saved = localStorage.getItem(STORAGE_KEY) as ThemeKey | null;
    const idx = saved ? THEMES.indexOf(saved) : -1;
    const resolved = idx >= 0 ? idx : 0;
    // Apply immediately during first render to prevent theme flash
    document.documentElement.setAttribute('data-theme', THEMES[resolved]);
    return resolved;
  });

  useEffect(() => {
    const theme = THEMES[index];
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem(STORAGE_KEY, theme);
  }, [index]);

  const cycle = useCallback(() => {
    setIndex((prev) => (prev + 1) % THEMES.length);
  }, []);

  return {
    theme: THEMES[index],
    label: LABELS[index],
    index: index + 1, // 1-based for display
    cycle,
  };
}
