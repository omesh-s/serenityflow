/** @type {import('tailwindcss').Config} */
export default {
    content: [
      "./index.html",
      "./src/**/*.{js,ts,jsx,tsx}",
    ],
    theme: {
      extend: {
        colors: {
          ocean: {
            50: '#f0f9ff',
            100: '#e0f2fe',
            200: '#bae6fd',
            300: '#7dd3fc',
            400: '#38bdf8',
            500: '#0ea5e9',
            600: '#0284c7',
            700: '#0369a1',
            800: '#075985',
            900: '#0c4a6e',
            950: '#082f49',
          },
          serenity: {
            light: '#e8f4f8',
            DEFAULT: '#b8dde6',
            dark: '#7fb3c2',
          },
          calm: {
            white: '#ffffff',
            cream: '#fefefe',
            mist: '#f5f9fa',
          },
        },
        animation: {
          'wave': 'wave 20s ease-in-out infinite',
          'float': 'float 6s ease-in-out infinite',
          'ripple': 'ripple 3s linear infinite',
          'breath': 'breath 4s ease-in-out infinite',
        },
        keyframes: {
          wave: {
            '0%, 100%': { transform: 'translateX(0%) translateY(0%)' },
            '50%': { transform: 'translateX(10%) translateY(-5%)' },
          },
          float: {
            '0%, 100%': { transform: 'translateY(0px)' },
            '50%': { transform: 'translateY(-20px)' },
          },
          ripple: {
            '0%': { transform: 'scale(0.8)', opacity: '1' },
            '100%': { transform: 'scale(2.5)', opacity: '0' },
          },
          breath: {
            '0%, 100%': { transform: 'scale(1)', opacity: '0.7' },
            '50%': { transform: 'scale(1.05)', opacity: '1' },
          },
        },
      },
    },
    plugins: [],
  }
  