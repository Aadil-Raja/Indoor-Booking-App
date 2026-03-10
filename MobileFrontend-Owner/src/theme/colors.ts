/** CourtHub Design System — color tokens */
export const Colors = {
    // Primary (Green)
    primary: '#10b981',
    primaryDark: '#059669',
    primaryDarker: '#047857',
    primaryLight: '#34d399',
    primaryLighter: '#6ee7b7',
    primaryPale: '#d1fae5',
    primaryBg: '#ecfdf5',

    // Secondary
    secondary: '#065f46',
    secondaryDark: '#064e3b',

    // Neutrals
    white: '#ffffff',
    black: '#000000',
    gray50: '#f9fafb',
    gray100: '#f3f4f6',
    gray200: '#e5e7eb',
    gray300: '#d1d5db',
    gray400: '#9ca3af',
    gray500: '#6b7280',
    gray600: '#4b5563',
    gray700: '#374151',
    gray800: '#1f2937',
    gray900: '#111827',

    // Status
    success: '#10b981',
    successBg: '#d1fae5',
    error: '#ef4444',
    errorBg: '#fee2e2',
    warning: '#f59e0b',
    warningBg: '#fef3c7',
    info: '#3b82f6',
    infoBg: '#dbeafe',
} as const;

export type ColorKey = keyof typeof Colors;
