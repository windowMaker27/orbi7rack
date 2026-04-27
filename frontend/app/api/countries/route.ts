import { NextResponse } from "next/server";

const SOURCES = [
  "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/ne_110m_admin_0_countries.geojson",
  "https://raw.githubusercontent.com/vasturiano/globe.gl/master/example/hexed-polygons/ne_110m_admin_0_countries.geojson",
];

export const dynamic = "force-dynamic";
export const revalidate = 86400; // 24h cache

export async function GET() {
  for (const url of SOURCES) {
    try {
      const res = await fetch(url, { next: { revalidate: 86400 } });
      if (!res.ok) continue;
      const data = await res.json();
      return NextResponse.json(data, {
        headers: { "Cache-Control": "public, max-age=86400" },
      });
    } catch {
      continue;
    }
  }
  return NextResponse.json({ error: "Failed to fetch countries" }, { status: 502 });
}
