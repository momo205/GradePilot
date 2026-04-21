import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{js,ts,jsx,tsx,mdx}"],
  // Custom component classes from globals.css (@layer components); keep if scanning ever misses a file.
  safelist: [
    "gp-page",
    "gp-container",
    "gp-card",
    "gp-card-pad",
    "gp-heading-1",
    "gp-heading-2",
    "gp-muted",
    "gp-btn",
    "gp-btn-ghost",
    "gp-link",
    "gp-input",
    "gp-textarea",
  ],
  theme: {
    extend: {
      colors: {
        background: "var(--background)",
        surface: "var(--surface)",
        border: "var(--border)",
        accent: "var(--accent)",
        text: "var(--text)",
        muted: "var(--muted)",
      },
    },
  },
  plugins: [],
};
export default config;
