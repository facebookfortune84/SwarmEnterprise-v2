import type { KnipConfig } from "knip";

const config: KnipConfig = {
  entry: [
    "frontend/src/main.tsx",
    "frontend/src/**/*.test.{ts,tsx}",
    "frontend/vite.config.ts",
    "frontend/src/test-setup.ts",
    "scripts/**/*.js",
  ],
  project: [
    "frontend/src/**/*.{ts,tsx}",
    "scripts/**/*.js",
  ],
  ignore: [
    "frontend/dist/**",
    "node_modules/**",
    "venv/**",
    ".venv/**",
    "**/__pycache__/**",
  ],
  ignoreDependencies: [
    // Dev-only tools referenced in configs rather than imports
    "postcss",
    "autoprefixer",
    "tailwindcss",
  ],
  rules: {
    classMembers: "warn",
    exports: "warn",
    types: "warn",
    unlisted: "error",
  },
};

export default config;
