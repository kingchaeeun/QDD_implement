/**
 * Tailwind CSS configuration (ESM) for the Chrome extension.
 * Maps design tokens from CSS variables to Tailwind color utilities.
 * @type {import('tailwindcss').Config}
 */
export default {
  content: ["./src/**/*.{js,jsx,ts,tsx,html}"],
  theme: {
    extend: {
      colors: {
        primary: "var(--primary)",
        "primary-foreground": "var(--primary-foreground)",
        secondary: "var(--secondary)",
        "secondary-foreground": "var(--secondary-foreground)",
        muted: "var(--muted)",
        "muted-foreground": "var(--muted-foreground)",
        accent: "var(--accent)",
        destructive: "var(--destructive)",
        background: "var(--background)",
        foreground: "var(--foreground)",
        border: "var(--border)",
      },
      fontFamily: {
        sans: ["-apple-system", "BlinkMacSystemFont", "Segoe UI", "Roboto", "sans-serif"],
      },
    },
  },
  plugins: [],
};
