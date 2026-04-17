/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        // MITRA brand palette aligned with the framework document
        teal: { 400: '#2db4a0', 500: '#1f9b89' },
        purple: { 400: '#7c5cbf', 500: '#6b4daa' },
        amber: { 400: '#e6a817', 500: '#cc9514' },
      },
    },
  },
  plugins: [],
}
