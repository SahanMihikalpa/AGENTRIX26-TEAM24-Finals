import type { Config } from "tailwindcss";

/**
 * Design tokens derived from the GovGuide Homepage mockup
 * (see docs/11-frontend-architecture.md §7).
 */
const config: Config = {
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        brand: {
          DEFAULT: "oklch(0.58 0.18 258)",
          hover: "oklch(0.52 0.185 259)",
          dark: "oklch(0.48 0.19 262)",
          soft: "oklch(0.95 0.03 258)",
        },
        surface: {
          DEFAULT: "#f7f7f5",
          raised: "oklch(1 0 0)",
        },
        ink: {
          900: "oklch(0.18 0.02 255)",
          800: "oklch(0.2 0.02 255)",
          700: "oklch(0.22 0.015 255)",
          600: "oklch(0.3 0.015 255)",
          500: "oklch(0.4 0.02 255)",
          400: "oklch(0.5 0.02 255)",
        },
        line: {
          DEFAULT: "oklch(0.9 0.005 255)",
          soft: "oklch(0.92 0.005 255)",
        },
        blob: {
          blue: "oklch(0.83 0.07 265)",
          amber: "oklch(0.85 0.08 55)",
        },
        verified: { bg: "#f0fdf4", border: "#bbf7d0", text: "#166534", dot: "#16a34a" },
        pending: { bg: "#fffbeb", border: "#fde68a", text: "#92400e", dot: "#d97706" },
      },
      fontFamily: {
        sans: [
          "-apple-system",
          "BlinkMacSystemFont",
          "SF Pro Display",
          "SF Pro Text",
          "Helvetica",
          "Arial",
          "sans-serif",
        ],
      },
      borderRadius: {
        xl: "16px",
        "2xl": "18px",
        "3xl": "22px",
      },
      boxShadow: {
        header: "0 4px 20px oklch(0.3 0.02 255 / 0.08)",
        soft: "0 12px 32px oklch(0.3 0.03 255 / 0.1)",
        card: "0 8px 24px oklch(0.3 0.02 255 / 0.08)",
        floaty: "0 6px 28px oklch(0.3 0.02 255 / 0.12)",
        brand: "0 4px 12px oklch(0.5 0.18 258 / 0.35)",
      },
      keyframes: {
        rise: {
          from: { opacity: "0", transform: "translateY(10px)" },
          to: { opacity: "1", transform: "translateY(0)" },
        },
        blink: { "0%,100%": { opacity: "1" }, "50%": { opacity: "0" } },
        pulse2: { "0%,100%": { opacity: "1" }, "50%": { opacity: "0.45" } },
      },
      animation: {
        rise: "rise 0.25s ease",
        "fade-up": "rise 0.6s ease both",
        blink: "blink 1s steps(1) infinite",
        pulse2: "pulse2 1.2s ease-in-out infinite",
      },
    },
  },
  plugins: [],
};

export default config;
