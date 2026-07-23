/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        gov: {
          navy: '#12324a',
          blue: '#203b82',
          royal: '#1d347a',
          gold: '#f5c400',
          teal: '#0f766e',
          mint: '#e6f4f1',
          paper: '#f7faf9',
          line: '#cbdedb',
        },
      },
      boxShadow: {
        soft: '0 12px 30px rgba(18, 50, 74, 0.08)',
        ministry: '0 20px 50px rgba(29, 52, 122, 0.13)',
      },
    },
  },
  plugins: [],
}
