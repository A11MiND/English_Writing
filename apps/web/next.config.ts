import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  transpilePackages: ["@english-ai-writing/shared"],
  devIndicators: false,
  async rewrites() {
    const apiProxyTarget = process.env.API_PROXY_TARGET;
    if (!apiProxyTarget) return [];
    return [
      {
        source: "/api/:path*",
        destination: `${apiProxyTarget.replace(/\/$/, "")}/api/:path*`,
      },
    ];
  },
};

export default nextConfig;
