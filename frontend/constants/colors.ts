// ─── Wakeel Design Tokens ─────────────────────────────────────────────────────

const Colors = {
  PRIMARY:        '#1E5631',
  PRIMARY_LIGHT:  '#2D7A47',
  PRIMARY_SUBTLE: '#EEF4F0',

  PEACH:          '#F2C4A0',
  PEACH_SOFT:     '#FDF0E8',
  YELLOW_SOFT:    '#F5E6A3',
  YELLOW_BG:      '#FDF8E1',
  SAGE:           '#A8C5B5',
  SAGE_SOFT:      '#EEF5F1',

  BACKGROUND:     '#FAF8F5',
  SURFACE:        '#FFFFFF',
  SURFACE_2:      '#F4F2EF',
  BORDER:         '#E8E4DF',

  TEXT_PRIMARY:   '#1A1A1A',
  TEXT_SECONDARY: '#5C5C5C',
  TEXT_MUTED:     '#9E9E9E',
  TEXT_ON_GREEN:  '#FFFFFF',

  DANGER:         '#C0392B',
  DANGER_BG:      '#FDF0EE',
  WARNING:        '#D48B2E',
  WARNING_BG:     '#FDF5E6',
  SUCCESS:        '#1E5631',
  SUCCESS_BG:     '#EEF4F0',

  OVERLAY:        'rgba(26,26,26,0.5)',
  OVERLAY_GREEN:  'rgba(30,86,49,0.08)',
};

export const Spacing = {
  XS: 4, SM: 8, MD: 16, LG: 24, XL: 32, XXL: 48,
};

export const Radius = {
  SM: 8, MD: 14, LG: 20, XL: 28, FULL: 999,
};

export const Shadow = {
  SM: { shadowColor: '#1A1A1A', shadowOffset: { width: 0, height: 1 }, shadowOpacity: 0.06, shadowRadius: 4, elevation: 2 },
  MD: { shadowColor: '#1A1A1A', shadowOffset: { width: 0, height: 3 }, shadowOpacity: 0.08, shadowRadius: 8, elevation: 4 },
  LG: { shadowColor: '#1E5631', shadowOffset: { width: 0, height: 6 }, shadowOpacity: 0.12, shadowRadius: 16, elevation: 8 },
};

export default Colors;
