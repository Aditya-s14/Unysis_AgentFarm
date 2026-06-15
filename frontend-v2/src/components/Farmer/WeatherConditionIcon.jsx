/**
 * Brand-coloured weather condition icons (SVG).
 */

const COLORS = {
  sun: '#FFC107',
  sunHot: 'var(--harvest-gold)',
  cloud: '#4A90E2',
  cloudDark: '#2196F3',
  cloudMuted: '#90CAF9',
  rain: '#2196F3',
  rainLight: '#64B5F6',
  fog: '#6B7280',
  lightning: '#FFC107',
};

function normalizeCondition(cond) {
  return String(cond || 'partly_cloudy').toLowerCase().replace(/\s+/g, '_');
}

function Sunny({ size }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" aria-hidden>
      <circle cx="12" cy="12" r="4.5" fill={COLORS.sun} />
      {[0, 45, 90, 135, 180, 225, 270, 315].map((deg) => (
        <line
          key={deg}
          x1="12"
          y1="2.5"
          x2="12"
          y2="5.5"
          stroke={COLORS.sunHot}
          strokeWidth="1.8"
          strokeLinecap="round"
          transform={`rotate(${deg} 12 12)`}
        />
      ))}
    </svg>
  );
}

function PartlyCloudy({ size }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" aria-hidden>
      <circle cx="8" cy="9" r="3.2" fill={COLORS.sun} />
      <line x1="8" y1="3" x2="8" y2="4.5" stroke={COLORS.sunHot} strokeWidth="1.5" strokeLinecap="round" />
      <line x1="4" y1="9" x2="5.5" y2="9" stroke={COLORS.sunHot} strokeWidth="1.5" strokeLinecap="round" />
      <line x1="5.2" y1="5.2" x2="6.3" y2="6.3" stroke={COLORS.sunHot} strokeWidth="1.5" strokeLinecap="round" />
      <path
        d="M17 16H8.5a3.5 3.5 0 1 1 1.1-6.8A4.2 4.2 0 0 1 17 11.5a3.2 3.2 0 0 1 .5 6.3"
        fill={COLORS.cloudMuted}
        stroke={COLORS.cloud}
        strokeWidth="1.2"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function Cloudy({ size }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" aria-hidden>
      <path
        d="M18.5 16H8.8a4 4 0 1 1 1.2-7.8A5 5 0 0 1 18.5 10a3.8 3.8 0 0 1 .8 6"
        fill={COLORS.cloudMuted}
        stroke={COLORS.cloud}
        strokeWidth="1.3"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function Rain({ size, heavy = false }) {
  const drops = heavy ? 4 : 3;
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" aria-hidden>
      <path
        d="M17.5 13H9a3.5 3.5 0 1 1 1-6.8A4.5 4.5 0 0 1 17.5 9a3 3 0 0 1 .5 4"
        fill={heavy ? COLORS.cloudDark : COLORS.cloudMuted}
        stroke={COLORS.cloudDark}
        strokeWidth="1.2"
        strokeLinejoin="round"
      />
      {Array.from({ length: drops }).map((_, i) => (
        <line
          key={i}
          x1={8 + i * 3.5}
          y1="15.5"
          x2={7 + i * 3.5}
          y2="19"
          stroke={heavy ? COLORS.rain : COLORS.rainLight}
          strokeWidth="1.6"
          strokeLinecap="round"
        />
      ))}
    </svg>
  );
}

function Storm({ size }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" aria-hidden>
      <path
        d="M17.5 12.5H9a3.5 3.5 0 1 1 1-6.8A4.5 4.5 0 0 1 17.5 8.5a3 3 0 0 1 .5 4"
        fill="#78909C"
        stroke="#546E7A"
        strokeWidth="1.2"
        strokeLinejoin="round"
      />
      <path d="M12.5 14.5 10.5 18h2l-1.5 3 3.5-4.5h-2l1-2.5z" fill={COLORS.lightning} stroke={COLORS.sunHot} strokeWidth="0.5" />
      <line x1="8" y1="16" x2="7" y2="19" stroke={COLORS.rain} strokeWidth="1.5" strokeLinecap="round" />
      <line x1="11.5" y1="16" x2="10.5" y2="19" stroke={COLORS.rain} strokeWidth="1.5" strokeLinecap="round" />
      <line x1="15" y1="16" x2="14" y2="19" stroke={COLORS.rain} strokeWidth="1.5" strokeLinecap="round" />
    </svg>
  );
}

function HeatWave({ size }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" aria-hidden>
      <circle cx="12" cy="12" r="4.5" fill={COLORS.sunHot} />
      {[0, 45, 90, 135, 180, 225, 270, 315].map((deg) => (
        <line
          key={deg}
          x1="12"
          y1="2"
          x2="12"
          y2="5"
          stroke="#E74C3C"
          strokeWidth="2"
          strokeLinecap="round"
          transform={`rotate(${deg} 12 12)`}
        />
      ))}
    </svg>
  );
}

function Fog({ size }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" aria-hidden>
      {[13, 16, 19].map((y) => (
        <line
          key={y}
          x1="4"
          y1={y}
          x2="20"
          y2={y}
          stroke={COLORS.fog}
          strokeWidth="1.8"
          strokeLinecap="round"
          opacity={y === 16 ? 0.85 : 0.55}
        />
      ))}
    </svg>
  );
}

export default function WeatherConditionIcon({ condition, size = 24, className, style }) {
  const key = normalizeCondition(condition);

  let icon;
  switch (key) {
    case 'clear':
    case 'sunny':
      icon = <Sunny size={size} />;
      break;
    case 'partly_cloudy':
      icon = <PartlyCloudy size={size} />;
      break;
    case 'cloudy':
      icon = <Cloudy size={size} />;
      break;
    case 'rain':
    case 'monsoon':
      icon = <Rain size={size} />;
      break;
    case 'heavy_rain':
      icon = <Rain size={size} heavy />;
      break;
    case 'storm':
      icon = <Storm size={size} />;
      break;
    case 'heat_wave':
      icon = <HeatWave size={size} />;
      break;
    case 'fog':
      icon = <Fog size={size} />;
      break;
    default:
      icon = <PartlyCloudy size={size} />;
  }

  return (
    <span
      className={className}
      style={{ display: 'inline-flex', alignItems: 'center', justifyContent: 'center', lineHeight: 0, ...style }}
      aria-hidden
    >
      {icon}
    </span>
  );
}

export function weatherIconBackground(condition) {
  const key = normalizeCondition(condition);
  if (key === 'clear' || key === 'sunny' || key === 'heat_wave') {
    return 'rgba(255, 193, 7, 0.18)';
  }
  if (key === 'rain' || key === 'heavy_rain' || key === 'monsoon' || key === 'storm') {
    return 'rgba(33, 150, 243, 0.15)';
  }
  if (key === 'cloudy' || key === 'partly_cloudy' || key === 'fog') {
    return 'rgba(74, 144, 226, 0.12)';
  }
  return 'rgba(74, 144, 226, 0.12)';
}
