import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./lib/**/*.{js,ts,jsx,tsx,mdx}"
  ],
  theme: {
    extend: {
      fontFamily: {
        mono: ["var(--font-geist-mono)", "ui-monospace", "SFMono-Regular", "Menlo", "monospace"],
        sans: ["var(--font-geist-sans)", "Inter", "ui-sans-serif", "system-ui", "sans-serif"]
      },
      colors: {
        terminal: {
          bg: "#08090a",
          panel: "#111315",
          line: "#24282c",
          ink: "#e7ecef",
          muted: "#8e9aa5",
          green: "#39d98a",
          cyan: "#49c6e5",
          amber: "#f2b84b",
          rose: "#ff6b7a"
        }
      }
    }
  },
  plugins: []
};

export default config;

