/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        canvas: '#FCFAF7', surface: '#FFFFFF', 'surface-muted': '#F7F5F2',
        ink: '#292624', muted: '#6F6965', faint: '#9A938E',
        brand: { DEFAULT: '#2F6F58', dark: '#245744', pale: '#E8F8EE' },
        coral: { DEFAULT: '#FF9D9D', dark: '#9B4B4B', pale: '#FFF0F0' },
        peach: { DEFAULT: '#FFC5AA', dark: '#95563E', pale: '#FFF3EC' },
        lime: { DEFAULT: '#EEF8CD', dark: '#68763C', pale: '#F8FCEB' },
        mint: { DEFAULT: '#BBF1D2', dark: '#2F6F58', pale: '#E8F8EE' },
        line: '#E9E5E1', 'line-light': '#F2EFEC', info: '#416A87',
      },
      boxShadow: {
        soft: '0 1px 2px rgba(41,38,36,.025), 0 10px 30px rgba(41,38,36,.045)',
        float: '0 18px 50px rgba(41,38,36,.10)',
      },
      borderRadius: { card: '18px' },
    },
  },
  plugins: [],
}
