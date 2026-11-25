/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: { 950: "#07080B", 900: "#0C0E13", 850: "#11141B", 800: "#161A23", 700: "#222836", 600: "#2E3546" },
        mist: { 100: "#F2F4F8", 300: "#C3C9D6", 400: "#9AA3B5", 500: "#6E788C" },
        signal: { 300: "#8CFFC9", 400: "#4DFFAE", 500: "#1EF08E", 600: "#0FBF6F" },
        amberx: { 400: "#FFC857" },
        rose: { 400: "#FF6B81" },
        sky: { 400: "#5CC8FF" },
      },
      fontFamily: {
        sans: ["Inter", "ui-sans-serif", "system-ui", "sans-serif"],
        display: ["'Space Grotesk'", "Inter", "ui-sans-serif", "sans-serif"],
        mono: ["'JetBrains Mono'", "ui-monospace", "monospace"],
      },
      boxShadow: {
        glow: "0 0 0 1px rgba(77,255,174,0.25), 0 10px 40px -10px rgba(30,240,142,0.35)",
      },
    },
  },
  plugins: [],
};
