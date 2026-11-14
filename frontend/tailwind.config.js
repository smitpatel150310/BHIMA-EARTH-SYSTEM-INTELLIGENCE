/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        bhima: {
          bg: '#F7F8F6',
          surface: '#FFFFFF',
          text: '#202824',
          muted: '#69736D',
          primary: '#31594B',
          'primary-hover': '#26463B',
          'primary-light': '#F0F4F2',
          secondary: '#84978B',
          border: '#E4E8E4',
          subtle: '#EEF1ED',
          danger: '#A8423F',
          warning: '#B2782A',
          success: '#387259',
        }
      },
      fontFamily: {
        sans: ['Inter', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'Roboto', 'sans-serif'],
      },
      borderRadius: {
        DEFAULT: '6px',
        sm: '4px',
        md: '6px',
        lg: '8px',
      }
    },
  },
  plugins: [],
};
