/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './src/pages/**/*.{js,jsx}',
    './src/components/**/*.{js,jsx}',
  ],
  theme: {
    extend: {
      colors: {
        canvas:    'var(--bg)',
        card:      'var(--bg-card)',
        line:      'var(--border)',
        accent:    'var(--accent)',
        navy:      'var(--navy)',
        paper:     'var(--text)',
        secondary: 'var(--text-secondary)',
        muted:     'var(--muted)',
        ok:        'var(--green-ok)',
        risk:      'var(--red-risk)',
        mandi:     'var(--blue-mandi)',
        purplelog: 'var(--purple-log)',
        orangedmd: 'var(--orange-dmd)',
      },
      fontFamily: {
        sans:  ['Inter', '-apple-system', 'system-ui', 'sans-serif'],
        serif: ['"Playfair Display"', 'Georgia', 'serif'],
        mono:  ['"JetBrains Mono"', 'ui-monospace', 'monospace'],
      },
      letterSpacing: {
        'wider-2': '0.15em',
        'wider-3': '0.2em',
      },
      borderRadius: {
        sharp: '2px',
        card: '4px',
      },
    },
  },
  plugins: [],
};
