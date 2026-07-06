import type { NextConfig } from 'next';

const nextConfig: NextConfig = {
  // En dev mobile (NEXT_PUBLIC_DEV_ORIGIN defini), on redirige le client
  // HMR vers l'IP reelle au lieu de localhost pour que Safari iOS
  // puisse etablir la connexion websocket et que React s'hydrate.
  ...(process.env.NEXT_PUBLIC_DEV_ORIGIN
    ? {
        experimental: {
          // Turbopack desactive (on utilise --webpack), mais on garde
          // la config hmr pour webpack dev server
        },
        webpackDevMiddleware: (config: any) => config,
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
};

export default nextConfig;
