import { useTheme } from '@/context/ThemeContext';

/**
 * Light / dark theme switch — icon + optional label.
 */
export default function DarkModeToggle({ collapsed = false, variant = 'sidebar' }) {
  const { isDark, toggleTheme, ready } = useTheme();

  if (!ready) return null;

  const label = isDark ? 'Light mode' : 'Dark mode';

  const baseStyle = variant === 'sidebar'
    ? {
        width: '100%',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        gap: 6,
        padding: '8px',
        borderRadius: 8,
        border: 'none',
        background: 'transparent',
        color: 'var(--sidebar-text-faint)',
        fontSize: 12,
        cursor: 'pointer',
        transition: 'color 0.15s, background 0.15s',
      }
    : {
        display: 'inline-flex',
        alignItems: 'center',
        gap: 6,
        padding: '6px 10px',
        borderRadius: 8,
        border: '1px solid var(--border)',
        background: 'var(--bg-card)',
        color: 'var(--text-secondary)',
        fontSize: 11,
        fontWeight: 500,
        cursor: 'pointer',
        transition: 'border-color 0.15s, background 0.15s',
      };

  return (
    <button
      type="button"
      onClick={toggleTheme}
      aria-label={label}
      title={label}
      style={baseStyle}
      onMouseEnter={(e) => {
        if (variant === 'sidebar') {
          e.currentTarget.style.color = 'var(--sidebar-text)';
          e.currentTarget.style.background = 'var(--sidebar-hover)';
        } else {
          e.currentTarget.style.borderColor = 'var(--accent)';
        }
      }}
      onMouseLeave={(e) => {
        if (variant === 'sidebar') {
          e.currentTarget.style.color = 'var(--sidebar-text-faint)';
          e.currentTarget.style.background = 'transparent';
        } else {
          e.currentTarget.style.borderColor = 'var(--border)';
        }
      }}
    >
      {isDark ? <SunIcon /> : <MoonIcon />}
      {(!collapsed || variant === 'header') && (
        <span className="font-mono uppercase" style={{ fontSize: variant === 'sidebar' ? 12 : 10, letterSpacing: '0.08em' }}>
          {variant === 'sidebar' ? label : (isDark ? 'Light' : 'Dark')}
        </span>
      )}
    </button>
  );
}

function MoonIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
      <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" />
    </svg>
  );
}

function SunIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
      <circle cx="12" cy="12" r="4" />
      <path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M4.93 19.07l1.41-1.41M17.66 6.34l1.41-1.41" />
    </svg>
  );
}
