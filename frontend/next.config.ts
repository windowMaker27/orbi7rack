import type { NextConfig } from 'next';

const devOrigin = process.env.NEXT_PUBLIC_DEV_ORIGIN;

const nextConfig: NextConfig = {
  // En dev mobile, NEXT_PUBLIC_DEV_ORIGIN = http://<TAILSCALE_IP>:3000
  // On force l'assetPrefix sur l'IP réelle pour que le client HMR
  // de Safari iOS puisse joindre le WebSocket (pas localhost cross-origin).
  ...(devOrigin
    ? {
        assetPrefix: devOrigin,
      }
    : {}),

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
    // En mode dev mobile, on redirige le client HMR WebSocket vers l'IP
    // Tailscale réelle. Sans ça, Next injecte ws://localhost:3000/_next/webpack-hmr
    // que Safari iOS refuse (cross-origin) -> pas d'hydratation React
    // -> event handlers JS jamais attachés au DOM.
    if (dev && !isServer && devOrigin) {
      const url = new URL(devOrigin);
      config.infrastructureLogging = { level: 'error' };

      // webpack-dev-server client options
      config.devServer = {
        ...config.devServer,
        client: {
          ...config.devServer?.client,
          webSocketURL: {
            hostname: url.hostname,
            port: Number(url.port) || 3000,
            protocol: 'ws',
          },
        },
      };
    }
    return config;
  },
};

export default nextConfig;
