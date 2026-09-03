/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        whatsapp: {
          green: '#25D366',
          dark: '#075E54',
          light: '#DCF8C6',
          teal: '#128C7E',
        },
        emporio: {
          primary: '#2E7D32',
          secondary: '#4CAF50',
          accent: '#81C784',
          dark: '#1B5E20',
        },
      },
    },
  },
  plugins: [],
}
