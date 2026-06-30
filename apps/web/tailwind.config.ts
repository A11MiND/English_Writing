import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{ts,tsx}", "../../packages/shared/src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#17201b",
        chalk: "#f8faf7",
        moss: "#406b54",
        coral: "#d86f45",
        paper: "#ffffff",
      },
      boxShadow: {
        soft: "0 18px 60px rgba(23, 32, 27, 0.10)",
      },
    },
  },
  plugins: [],
};

export default config;
