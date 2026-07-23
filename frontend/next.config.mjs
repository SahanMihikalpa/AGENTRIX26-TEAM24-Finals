/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // Emit a self-contained server bundle (.next/standalone) that traces only the
  // modules actually imported. The Docker runtime stage ships that instead of
  // node_modules — ~200 MB rather than ~1.5 GB. No effect on `next dev`.
  output: "standalone",
};

export default nextConfig;
