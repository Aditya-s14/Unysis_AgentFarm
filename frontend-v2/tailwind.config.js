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
        forest:    'var(--forest)',
        sage:      'var(--sage)',
        mint:      'var(--mint)',
        sky:       'var(--sky-blue)',
        water:     'var(--water-blue)',
        gold:      'var(--harvest-gold)',
        amber:     'var(--amber)',
      },
      fontFamily: {
        sans:    ['"IBM Plex Sans"', '-apple-system', 'system-ui', 'sans-serif'],
        heading: ['"IBM Plex Sans"', '-apple-system', 'system-ui', 'sans-serif'],
        serif:   ['"IBM Plex Sans"', '-apple-system', 'system-ui', 'sans-serif'],
        mono:    ['"IBM Plex Sans"', '-apple-system', 'system-ui', 'sans-serif'],
      },
      letterSpacing: {
        'wider-2': '0.15em',
        'wider-3': '0.20em',
      },
      borderRadius: {
        sharp: '2px',
        card:  '4px',
      },
    },
  },
  plugins: [],
};
