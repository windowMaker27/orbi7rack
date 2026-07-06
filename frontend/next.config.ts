import type { NextConfig } from 'next';

const devOrigin = process.env.NEXT_PUBLIC_DEV_ORIGIN;

const nextConfig: NextConfig = {
  async headers() {
    return [
      {
        source: '/:path*',
        headers: [
          { key: 'Access-Control-Allow-Origin', value: '*' },
        ],
      },
    ];
  },

  webpack(config, { dev, isServer }) {
    // En mode dev mobile uniquement : redirige le client HMR
    // vers l'IP Tailscale au lieu de localhost.
    // Sans ca, Safari iOS refuse la connexion websocket cross-origin
    // -> React ne s'hydrate pas -> onClick/onSubmit jamais attaches.
    if (dev && !isServer && devOrigin) {
      const url = new URL(devOrigin);
      config.infrastructureLogging = { level: 'error' };
      // Next.js webpack dev server : on force le webSocketURL
      if (config.devServer) {
        config.devServer.client = {
          ...config.devServer.client,
          webSocketURL: {
            hostname: url.hostname,
            port: Number(url.port) || 3000,
            protocol: 'ws',
          },
        };
      }
      // Fallback : injecte directement dans les entries HMR
      const hotClient = `webpack-hot-middleware/client?path=http://${url.hostname}:${url.port || 3000}/_next/webpack-hmr&reload=true&overlay=false`;
      if (Array.isArray(config.entry)) {
        config.entry = [hotClient, ...config.entry];
      } else if (typeof config.entry === 'function') {
        const originalEntry = config.entry;
        config.entry = async () => {
          const entries = await originalEntry();
          if (entries['main.js'] && !entries['main.js'].includes(hotClient)) {
            entries['main.js'].unshift(hotClient);
          }
          return entries;
        };
      }
    }
    return config;
  },
};

export default nextConfig;
