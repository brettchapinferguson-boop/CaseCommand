/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        navy: {
          50: '#f4f6fb',
          100: '#e6ecf5',
          200: '#c9d6e8',
          300: '#9cb3d3',
          400: '#6987b6',
          500: '#47679c',
          600: '#365183',
          700: '#2c416a',
          800: '#1f2e4d',
          900: '#0f1b35',
          950: '#080f1f',
        },
        gold: {
          50: '#fbf8ef',
          100: '#f6eed7',
          200: '#ecdaa6',
          300: '#dfc070',
          400: '#cea84a',
          500: '#b78d33',
          600: '#9a7029',
          700: '#7a5523',
          800: '#5d4220',
          900: '#4a3520',
        },
        charcoal: {
          50: '#f5f6f7',
          100: '#e6e8ea',
          200: '#cdd1d6',
          300: '#a5acb5',
          400: '#74808d',
          500: '#566372',
          600: '#434e5c',
          700: '#37404b',
          800: '#2a3038',
          900: '#1c2026',
        },
      },
      fontFamily: {
        sans: [
          'Inter',
          'ui-sans-serif',
          'system-ui',
          '-apple-system',
          'BlinkMacSystemFont',
          'Segoe UI',
          'Roboto',
          'Helvetica Neue',
          'Arial',
          'sans-serif',
        ],
        serif: [
          'Source Serif Pro',
          'Georgia',
          'Cambria',
          'Times New Roman',
          'serif',
        ],
      },
      boxShadow: {
        card: '0 1px 2px rgba(15,27,53,0.06), 0 8px 24px rgba(15,27,53,0.06)',
        cardHover:
          '0 4px 12px rgba(15,27,53,0.08), 0 20px 40px rgba(15,27,53,0.12)',
      },
      backgroundImage: {
        'grid-navy':
          'linear-gradient(rgba(255,255,255,0.06) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.06) 1px, transparent 1px)',
      },
      keyframes: {
        fadeUp: {
          '0%': { opacity: '0', transform: 'translateY(8px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
      },
      animation: {
        fadeUp: 'fadeUp 0.6s ease-out both',
      },
    },
  },
  plugins: [],
};
