export interface LatLon {
  lat: number
  lon: number
}

const EARTH_RADIUS_M = 6_371_008.8
export const MPS_TO_KNOTS = 3600 / 1852

const toRad = (deg: number) => (deg * Math.PI) / 180
const toDeg = (rad: number) => (rad * 180) / Math.PI

/** 大圓距離（公尺） */
export function haversineM(a: LatLon, b: LatLon): number {
  const dLat = toRad(b.lat - a.lat)
  const dLon = toRad(b.lon - a.lon)
  const h = Math.sin(dLat / 2) ** 2 + Math.cos(toRad(a.lat)) * Math.cos(toRad(b.lat)) * Math.sin(dLon / 2) ** 2
  return 2 * EARTH_RADIUS_M * Math.asin(Math.min(1, Math.sqrt(h)))
}

/** a → b 的初始方位角：真北為 0，順時針，範圍 [0, 360) */
export function bearingDeg(a: LatLon, b: LatLon): number {
  const phi1 = toRad(a.lat)
  const phi2 = toRad(b.lat)
  const dLon = toRad(b.lon - a.lon)
  const y = Math.sin(dLon) * Math.cos(phi2)
  const x = Math.cos(phi1) * Math.sin(phi2) - Math.sin(phi1) * Math.cos(phi2) * Math.cos(dLon)
  return (toDeg(Math.atan2(y, x)) + 360) % 360
}

export interface Motion {
  speedKnots: number // 對地航速 SOG
  courseDeg: number | null // 對地航向 COG；幾乎沒有移動時無法判斷，為 null
}

/** 用最近 window 段位移（頭尾兩點）估算航速與航向，平滑掉單點抖動 */
export function estimateMotion(track: readonly (LatLon & { t: number })[], window = 5): Motion | null {
  if (track.length < 2) return null
  const a = track[Math.max(0, track.length - 1 - window)]!
  const b = track[track.length - 1]!
  const dt = (b.t - a.t) / 1000
  if (dt <= 0) return null
  const dist = haversineM(a, b)
  return {
    speedKnots: (dist / dt) * MPS_TO_KNOTS,
    courseDeg: dist < 0.5 ? null : bearingDeg(a, b),
  }
}

/** 十進位度數轉度分秒，例如 22.6166 → 22°36'59.8"N */
export function formatDms(value: number, axis: 'lat' | 'lon'): string {
  const hemisphere = axis === 'lat' ? (value >= 0 ? 'N' : 'S') : value >= 0 ? 'E' : 'W'
  const totalTenths = Math.round(Math.abs(value) * 36000) // 以 0.1 秒為單位，避免進位成 60.0"
  const deg = Math.floor(totalTenths / 36000)
  const min = Math.floor((totalTenths % 36000) / 600)
  const sec = (totalTenths % 600) / 10
  return `${deg}°${String(min).padStart(2, '0')}'${sec.toFixed(1).padStart(4, '0')}"${hemisphere}`
}
