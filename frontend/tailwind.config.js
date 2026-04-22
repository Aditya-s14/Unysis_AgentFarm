/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './src/pages/**/*.{js,jsx}',
    './src/components/**/*.{js,jsx}',
  ],
  theme: {
    extend: {
      colors: {
        agri: {
          green: '#2e7d32',
          'green-dark': '#1b5e20',
          'green-light': '#a5d6a7',
          orange: '#ef6c00',
          'orange-light': '#ffb74d',
          soil: '#795548',
          cream: '#fff8e1',
        },
      },
    },
  },
  plugins: [],
};
