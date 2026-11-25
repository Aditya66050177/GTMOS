/** @type {import('tailwindcss').Config} */
// GTMOS design tokens. Contrast (WCAG) measured on white unless noted:
// ink 17.8 · ink-2 10.5 · ink-3 7.7 · ink-4 5.0 (4.6 on canvas) · accent-600 5.5
// warn-700 on warn-50 5.2 · danger-700 on danger-50 6.1 · line-input 3.3 (UI boundary)
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        canvas: "#F6F7F9",
        surface: "#FFFFFF",
        subtle: "#F9FAFB",
        line: { DEFAULT: "#E4E7EC", strong: "#D0D5DD", input: "#868E9C" },
        ink: { DEFAULT: "#101828", 2: "#344054", 3: "#475467", 4: "#667085" },
        neutral: { 100: "#F2F4F7", 200: "#EAECF0" },
        accent: { 50: "#F0FDFA", 100: "#CCFBF1", 300: "#2DD4BF", 600: "#0F766E", 700: "#115E59", 800: "#134E4A" },
        warn: { 50: "#FFFAEB", 200: "#FEDF89", 700: "#B54708" },
        danger: { 50: "#FEF3F2", 200: "#FECDCA", 700: "#B42318" },
      },
      fontFamily: {
        sans: ["Inter", "ui-sans-serif", "system-ui", "-apple-system", "Segoe UI", "sans-serif"],
        mono: ["ui-monospace", "SFMono-Regular", "Menlo", "Consolas", "monospace"],
      },
      fontSize: { "2xs": ["0.6875rem", { lineHeight: "1rem" }] },
      boxShadow: { card: "0 1px 2px rgba(16, 24, 40, 0.05)" },
    },
  },
  plugins: [],
};
