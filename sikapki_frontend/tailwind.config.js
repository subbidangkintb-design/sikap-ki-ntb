/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        gov: {
          navy: '#12324a',
          blue: '#1d5f82',
          teal: '#0f766e',
          mint: '#e6f4f1',
          paper: '#f7faf9',
          line: '#cbdedb',
        },
      },
      boxShadow: {
        soft: '0 12px 30px rgba(18, 50, 74, 0.08)',
      },
    },
  },
  plugins: [],
}
