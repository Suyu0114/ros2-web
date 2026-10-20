/** 與 backend/app/schemas.py 的 GpsFix 一致 */
export interface GpsFix {
  seq: number // bridge 收到的第幾筆有效 fix，單調遞增
  t: number // header.stamp，epoch 毫秒
  lat: number
  lon: number
  alt: number | null
  status: number
  frame_id: string
}

/**
 * WebSocket /ws/gps 推送的訊息：連線後先一則 snapshot，之後每筆一則 fix。
 * session 在 backend 每次啟動時都不同（重啟後歷史清空、seq 從 1 重新編號）。
 */
export type ServerMessage =
  | { type: 'snapshot'; session: string; points: GpsFix[] }
  | { type: 'fix'; data: GpsFix }

export type ConnectionStatus = 'connecting' | 'open' | 'closed'
