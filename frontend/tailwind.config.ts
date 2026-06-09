import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}", "./lib/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        navy: "#13294B",
        orange: "#FF5F05",
        bg: "#F8FAFC",
        card: "#FFFFFF",
        text: "#111827",
        muted: "#6B7280",
        success: "#16A34A",
        warning: "#F59E0B",
        danger: "#DC2626"
      },
      boxShadow: {
        panel: "0 20px 45px rgba(15, 23, 42, 0.08)",
      },
      borderRadius: {
        xl2: "1rem"
      },
      backgroundImage: {
        "illinois-grid": "radial-gradient(circle at 10% 20%, rgba(255,95,5,0.11) 0%, transparent 35%), radial-gradient(circle at 85% 10%, rgba(19,41,75,0.15) 0%, transparent 45%)"
      }
    },
  },
  plugins: [],
};

export default config;
