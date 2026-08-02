import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  turbopack: {},
  env: {
    NEXT_PUBLIC_AI_BACKEND_URL: process.env.NEXT_PUBLIC_AI_BACKEND_URL || 'http://localhost:8000',
  },
  webpack(config) {
    config.module.rules.push({
      test: /\.svg$/i,
      issuer: /\.[jt]sx?$/,
      use: ["@svgr/webpack"],
    });

    return config;
  },
};

export default nextConfig;
