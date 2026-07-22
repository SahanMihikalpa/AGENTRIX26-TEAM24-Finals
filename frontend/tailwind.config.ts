import type { Config } from "tailwindcss";

/**
 * Design tokens derived from the GovGuide.dc.html mockup
 * (see docs/11-frontend-architecture.md §7).
 */
const config: Config = {
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        brand: {
          DEFAULT: "#1F6FEB",
          hover: "#1a5fd0",
          soft: "#eff6ff",
        },
        verified: { bg: "#f0fdf4", border: "#bbf7d0", text: "#166534", dot: "#16a34a" },
        pending: { bg: "#fffbeb", border: "#fde68a", text: "#92400e", dot: "#d97706" },
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "-apple-system", "sans-serif"],
      },
      borderRadius: {
        xl: "16px",
        "2xl": "18px",
      },
      keyframes: {
        rise: {
          from: { opacity: "0", transform: "translateY(8px)" },
          to: { opacity: "1", transform: "translateY(0)" },
        },
        blink: { "0%,100%": { opacity: "1" }, "50%": { opacity: "0" } },
        pulse2: { "0%,100%": { opacity: "1" }, "50%": { opacity: "0.45" } },
      },
      animation: {
        rise: "rise 0.25s ease",
        blink: "blink 1s steps(1) infinite",
        pulse2: "pulse2 1.2s ease-in-out infinite",
      },
    },
  },
  plugins: [],
};

export default config;
