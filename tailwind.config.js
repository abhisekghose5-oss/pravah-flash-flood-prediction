export default {
  content: [
    "./index.html",
    "./map.html",
    "./weather.html",
    "./awareness.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
      },
      colors: {
        slate: {
          850: '#151f33',
          950: '#060a12',
        },
      },
    },
  },
  plugins: [],
};
