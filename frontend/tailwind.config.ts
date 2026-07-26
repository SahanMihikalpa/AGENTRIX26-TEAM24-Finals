import type { Config } from "tailwindcss";

/**
 * Design tokens for GovGuide. Refined to a warm "paper" system (see the design
 * comp): a calm off-white page, near-navy ink, and a serif display face for
 * headings — trustworthy and institutional without feeling cold or dated. Brand
 * blue and the verified/pending trust colours are unchanged.
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
        // Warm paper surfaces + hairlines.
        paper: {
          DEFAULT: "#f4f2ec", // page background
          raised: "#fbfaf7", // quiet raised chips/buttons
          sunken: "#faf9f5", // table footers, inset panels
          border: "#e6e2d8", // chrome + section rules
          line: "#e7e5df", // card borders
          hair: "#eceadf", // faint hairlines inside cards
        },
        // Near-navy ink scale for text.
        ink: {
          DEFAULT: "#14213d",
          soft: "#4b5563",
          muted: "#6b7280",
          faint: "#9aa2ae",
        },
        // The dark differentiator band on the landing page.
        night: "#0e1b33",
      },
      fontFamily: {
        // The next/font CSS variables already resolve to the quoted family name
        // plus a metrics-matched fallback (e.g. `"Source Serif 4", "Source Serif
        // 4 Fallback"`). Listing a bare multi-word name here would emit it
        // *unquoted* — `Source Serif 4` — which is invalid CSS and makes the
        // browser drop the whole declaration. So only single-word generics follow.
        sans: ["var(--font-inter)", "system-ui", "-apple-system", "sans-serif"],
        serif: ["var(--font-serif)", "Georgia", "serif"],
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
        rise: "rise 0.28s ease both",
        blink: "blink 1s steps(1) infinite",
        pulse2: "pulse2 1.2s ease-in-out infinite",
      },
    },
  },
  plugins: [],
};

export default config;
