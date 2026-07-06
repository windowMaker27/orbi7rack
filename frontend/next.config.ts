import type { NextConfig } from 'next';

const nextConfig: NextConfig = {
  // Next.js 15+ bloque les ressources dev cross-origin par defaut.
  // Safari iOS arrive depuis l'IP Tailscale (ex: 100.86.47.88) au lieu
  // de localhost -> React runtime bloque -> pas d'hydratation -> boutons muets.
  allowedDevOrigins: [
    '100.*.*.*',
    process.env.NEXT_PUBLIC_DEV_ORIGIN ?? '',
  ].filter(Boolean) as string[],

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
