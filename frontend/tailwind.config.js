/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        brand: {
          50:  '#f0f4ff',
          100: '#dde6ff',
          500: '#4f6ef7',
          600: '#3a56e8',
          700: '#2d44cc',
        },
      },
    },
  },
  plugins: [],
}


