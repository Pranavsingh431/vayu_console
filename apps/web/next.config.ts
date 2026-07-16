import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  // `@vayu/shared` is a workspace package shipped as raw TypeScript; Next must
  // compile it rather than expecting a pre-built dist.
  transpilePackages: ["@vayu/shared"],
  // Fail the build on type or lint errors rather than shipping them to Vercel.
  typescript: { ignoreBuildErrors: false },
  eslint: { ignoreDuringBuilds: false },
};

export default nextConfig;
