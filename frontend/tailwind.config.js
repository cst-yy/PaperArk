/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        primary: {
          50: "#e6f1fb",
          100: "#b5d4f4",
          200: "#85b7eb",
          400: "#378add",
          500: "#185fa5",
          600: "#0c447c",
          700: "#042c53",
        },
      },
    },
  },
  plugins: [],
};
