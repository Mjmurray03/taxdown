// Design Tokens for Taxdown Premium UI
// Systematically organized design values for consistent styling

export const colors = {
  // Primary Background
  white: '#FFFFFF',
  warmGray: '#FAFAF9',
  charcoal: '#18181B',

  // Text Hierarchy
  textPrimary: '#09090B',
  textSecondary: '#71717A',
  textTertiary: '#A1A1AA',
  textDisabled: '#D4D4D8',

  // Accent Colors
  actionPrimary: '#18181B',
  successDeep: '#166534',
  successBg: '#DCFCE7',
  warningDeep: '#A16207',
  warningBg: '#FEF3C7',
  errorDeep: '#991B1B',
  errorBg: '#FEE2E2',
  infoDeep: '#1E40AF',

  // Data Visualization
  chartPrimary: '#18181B',
  chartSecondary: '#71717A',
  chartTertiary: '#A1A1AA',
  chartQuaternary: '#D4D4D8',
  chartPositive: '#166534',
  chartNegative: '#991B1B',

  // Borders & Dividers
  borderSubtle: '#E4E4E7',
  borderHover: '#D4D4D8',
  borderFocus: '#18181B',

  // Neutral Backgrounds
  neutralBg: '#F4F4F5',
  neutralHover: '#FAFAF9',
} as const;

export const typography = {
  // Font Families
  fontPrimary: "'Inter', system-ui, -apple-system, sans-serif",
  fontMono: "'JetBrains Mono', 'SF Mono', 'Consolas', monospace",

  // Type Scale (Perfect Fourth - 1.333)
  display: {
    size: '3rem',      // 48px
    weight: '600',
    lineHeight: '1.1',
    letterSpacing: '-0.02em',
  },
  h1: {
    size: '2.25rem',   // 36px
    weight: '600',
    lineHeight: '1.2',
    letterSpacing: '-0.02em',
  },
  h2: {
    size: '1.688rem',  // 27px
    weight: '600',
    lineHeight: '1.3',
    letterSpacing: '-0.01em',
  },
  h3: {
    size: '1.25rem',   // 20px
    weight: '600',
    lineHeight: '1.4',
    letterSpacing: '-0.01em',
  },
  bodyLarge: {
    size: '1.125rem',  // 18px
    weight: '400',
    lineHeight: '1.6',
  },
  body: {
    size: '1rem',      // 16px
    weight: '400',
    lineHeight: '1.5',
  },
  bodySmall: {
    size: '0.875rem',  // 14px
    weight: '400',
    lineHeight: '1.5',
  },
  caption: {
    size: '0.75rem',   // 12px
    weight: '500',
    lineHeight: '1.4',
    letterSpacing: '0.02em',
    textTransform: 'uppercase' as const,
  },
  monoData: {
    size: '0.875rem',  // 14px
    weight: '500',
    fontVariantNumeric: 'tabular-nums',
  },
} as const;

export const spacing = {
  xs: '0.25rem',    // 4px
  sm: '0.5rem',     // 8px
  md: '0.75rem',    // 12px
  base: '1rem',     // 16px
  lg: '1.5rem',     // 24px
  xl: '2rem',       // 32px
  '2xl': '3rem',    // 48px
  '3xl': '4rem',    // 64px
  '4xl': '6rem',    // 96px
} as const;

export const shadows = {
  elevation1: '0 1px 2px rgba(0,0,0,0.04), 0 1px 3px rgba(0,0,0,0.06)',
  elevation2: '0 4px 6px rgba(0,0,0,0.04), 0 2px 4px rgba(0,0,0,0.06)',
  elevation3: '0 10px 15px rgba(0,0,0,0.06), 0 4px 6px rgba(0,0,0,0.08)',
  elevation4: '0 20px 25px rgba(0,0,0,0.08), 0 10px 10px rgba(0,0,0,0.06)',
} as const;

export const borderRadius = {
  small: '6px',
  medium: '8px',
  large: '12px',
} as const;

export const animation = {
  durationMicro: '100ms',
  durationStandard: '200ms',
  durationEmphasis: '300ms',
  easingDefault: 'cubic-bezier(0.4, 0, 0.2, 1)',
  easingEnter: 'cubic-bezier(0, 0, 0.2, 1)',
  easingExit: 'cubic-bezier(0.4, 0, 1, 1)',
} as const;

export const layout = {
  navHeight: '64px',
  sidebarWidth: '240px',
  sidebarWidthCollapsed: '64px',
  maxContentWidth: '1440px',
  pageHorizontalPadding: '48px',
  pageVerticalPadding: '32px',
} as const;

export const components = {
  button: {
    height: '40px',
    heightSmall: '32px',
    heightLarge: '44px',
    paddingX: '16px',
    fontSize: '14px',
    fontWeight: '500',
  },
  input: {
    height: '40px',
    paddingX: '12px',
    fontSize: '14px',
    borderWidth: '1px',
    focusRingWidth: '2px',
    focusRingOffset: '2px',
  },
  card: {
    padding: '24px',
    borderWidth: '1px',
  },
  table: {
    headerHeight: '40px',
    rowHeight: '52px',
    cellPaddingX: '16px',
  },
  badge: {
    paddingX: '8px',
    paddingY: '4px',
    fontSize: '12px',
    fontWeight: '500',
  },
} as const;
