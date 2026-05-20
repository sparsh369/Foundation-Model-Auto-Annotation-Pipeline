import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        brand: { DEFAULT: "#4f46e5", dark: "#4338ca" },
        ok: "#16a34a",
        warn: "#d97706",
        danger: "#dc2626",
      },
    },
  },
  plugins: [],
};
export default config;
