export default {
  content: [
    "./index.html",
    "./map.html",
    "./weather.html",
    "./awareness.html",
    "./community.html",
    "./alerts.html",
    "./evacuation.html",
    "./xai.html",
    "./digital_twin.html",
    "./simulation.html",
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
