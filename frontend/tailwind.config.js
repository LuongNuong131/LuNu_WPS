/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{vue,js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: "#2563eb", // Tailwind Blue 600
        secondary: "#475569", // Tailwind Slate 600
      }
    },
  },
  plugins: [],
}