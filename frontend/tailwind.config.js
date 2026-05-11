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
        paper:     'var(--text)',
        muted:     'var(--muted)',
        ok:        'var(--green-ok)',
        risk:      'var(--red-risk)',
        mandi:     'var(--blue-mandi)',
        purplelog: 'var(--purple-log)',
        orangedmd: 'var(--orange-dmd)',
      },
      fontFamily: {
        syne: ['Syne', 'system-ui', 'sans-serif'],
        mono: ['"DM Mono"', 'ui-monospace', 'monospace'],
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
