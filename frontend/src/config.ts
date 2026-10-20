export interface AppConfig {
  tileUrl: string
  tileAttribution: string
}

const OSM_DEFAULT: AppConfig = {
  tileUrl: 'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
  tileAttribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
}

/**
 * 讀取 nginx 依環境變數產生的 /config.json（TILE_URL、TILE_ATTRIBUTION）。
 * 同一個 image 可以部署到不同站點，例如隔離網路裡改用離線圖資伺服器。
 * 讀不到（例如 npm run dev）或沒設定時，使用 OpenStreetMap。
 */
export async function loadConfig(): Promise<AppConfig> {
  try {
    const response = await fetch('/config.json', { cache: 'no-store' })
    if (!response.ok) return OSM_DEFAULT
    const raw = (await response.json()) as Partial<AppConfig>
    if (!raw.tileUrl) return OSM_DEFAULT
    return { tileUrl: raw.tileUrl, tileAttribution: raw.tileAttribution ?? '' }
  } catch {
    return OSM_DEFAULT
  }
}
