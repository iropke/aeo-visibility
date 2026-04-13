import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        primary: {
          DEFAULT: "#5eb6b2",
          hover: "#22908b",
          pressed: "#15716d",
        },
        gs: {
          primary: "#232329",
          "secondary-1": "#68687b",
          "secondary-2": "#a1a1af",
          "tertiary-1": "#b0b0bc",
          "tertiary-2": "#d0d0d7",
          "quarterly-1": "#dfdfe4",
          "bg-darker": "#f3f4f7",
          bg: "#fafafa",
          white: "#ffffff",
          black: "#000000",
        },
      },
      fontFamily: {
        body: ["var(--font-body)"],
        display: ["var(--font-display)"],
        serif: ["var(--font-accent-serif)"],
      },
      borderRadius: {
        card: "28px",
        pill: "999px",
      },
      maxWidth: {
        shell: "1440px",
      },
    },
  },
  plugins: [],
};
export default config;
