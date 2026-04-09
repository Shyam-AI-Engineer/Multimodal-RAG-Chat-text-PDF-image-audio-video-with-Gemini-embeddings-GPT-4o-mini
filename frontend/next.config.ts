import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  // Allow images from any source (for source cards)
  images: {
    remotePatterns: [],
  },
};

export default nextConfig;
