/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        "nb-yellow": "#ffe083",
        "nb-yellow-bright": "#facc15",
        "nb-pink": "#ffb1c5",
        "nb-magenta": "#e30071",
        "nb-cyan": "#00eefc",
        "nb-cyan-light": "#7df4ff",
        "nb-green": "#4ade80",
        "nb-green-bright": "#10b981",
        "nb-bg": "#fbf8ef",
        "nb-paper": "#faf7f2",
        "nb-ink": "#121212",
        "neo-pink": "#ff2a85",
        "neo-cyan": "#00f0ff",
        "neo-yellow": "#facc15",
        "neo-green": "#10b981",
        "neo-bg": "#fbf8ef",
        "neo-black": "#121212",
      },
      fontFamily: {
        sans: ["ui-sans-serif", "system-ui", "Segoe UI", "Helvetica Neue", "Arial", "sans-serif"],
        display: ["ui-sans-serif", "system-ui", "Segoe UI", "Helvetica Neue", "Arial", "sans-serif"],
        grotesk: ["ui-sans-serif", "system-ui", "Segoe UI", "sans-serif"],
        mono: ["ui-monospace", "SFMono-Regular", "Menlo", "Consolas", "monospace"],
      },
      boxShadow: {
        "nb-sm": "2px 2px 0 0 #000",
        nb: "3px 3px 0 0 #000",
        "nb-lg": "4px 4px 0 0 #000",
        "nb-xl": "6px 6px 0 0 #000",
        neo: "4px 4px 0 0 #000",
        "neo-sm": "2px 2px 0 0 #000",
        "neo-lg": "6px 6px 0 0 #000",
      },
    },
  },
  plugins: [],
};
