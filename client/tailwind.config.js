// tailwind.config.js
export default {
  theme: {
    extend: {
      colors: {
        accent: '#22c55e', // verde (ou outro código desejado)
        primary: '#1e293b',
        secondary: '#f1f5f9',
        muted: '#cbd5e1',
        dark: '#0f172a',
      },
    },
  },
  content: ['./index.html', './src/**/*.{js,jsx}'],
  plugins: [],
}