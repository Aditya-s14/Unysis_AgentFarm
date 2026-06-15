const ROLE_COLORS_LIGHT = {
  fpo:    { bg: 'rgba(10,61,46,0.12)',   text: '#0A3D2E', dot: '#0A3D2E' },
  farmer: { bg: 'rgba(34,160,107,0.15)', text: '#22A06B', dot: '#22A06B' },
  driver: { bg: 'rgba(255,193,7,0.18)',  text: 'var(--amber-warn)', dot: '#FFC107' },
  mandi:  { bg: 'rgba(33,150,243,0.15)', text: '#2196F3', dot: '#2196F3' },
};

const ROLE_COLORS_DARK = {
  fpo:    { bg: 'rgba(34,160,107,0.28)',  text: '#8FE5B8', dot: '#22A06B' },
  farmer: { bg: 'rgba(34,160,107,0.22)',  text: '#6FD4A8', dot: '#22A06B' },
  driver: { bg: 'rgba(255,193,7,0.28)',   text: '#FFD966', dot: '#FFC107' },
  mandi:  { bg: 'rgba(33,150,243,0.28)',  text: '#7EC8F7', dot: '#2196F3' },
};

export function getRoleColors(role, isDark) {
  const palette = isDark ? ROLE_COLORS_DARK : ROLE_COLORS_LIGHT;
  return palette[role] || palette.fpo;
}
