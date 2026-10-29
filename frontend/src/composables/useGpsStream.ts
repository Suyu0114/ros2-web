import { computed, onScopeDispose, ref, shallowRef } from 'vue'

import type { ConnectionStatus, GpsFix, ServerMessage } from '../types'

export interface GpsStreamOptions {
  url?: string
  maxPoints?: number // 前端保留的軌跡點數上限
  WebSocketImpl?: new (url: string) => WebSocket // 測試時注入假的 WebSocket
  initialRetryMs?: number
  maxRetryMs?: number
  staleAfterMs?: number // 超過這麼久沒收到 fix，目前位置視為過期
}

const RATE_WINDOW_MS = 5000

/** 與頁面同源的 WebSocket 位址；正式環境由 nginx、開發時由 Vite proxy 轉給 backend */
export function defaultStreamUrl(location: Pick<Location, 'protocol' | 'host'> = window.location): string {
  return `${location.protocol === 'https:' ? 'wss' : 'ws'}://${location.host}/ws/gps`
}

/**
 * 連線到 /ws/gps，維護即時軌跡。
 * - 斷線後以指數退避自動重連（1 → 2 → 4 … 最多 10 秒）。
 * - 重連後的 snapshot：同一個 backend session 就用它補上斷線期間的點；backend 重啟過
 *   （session 不同、歷史已清空）則保留畫面上已有的航跡，再接上新的資料。
 * - track 每次都換成新的陣列（不就地修改），元件可以直接 watch。
 * - stale：斷線中，或太久沒收到即時 fix。畫面上的船位只是「最後已知位置」，不能當成目前位置。
 *   snapshot 是歷史，不算收到新資料。
 */
export function useGpsStream(options: GpsStreamOptions = {}) {
  const {
    url = defaultStreamUrl(),
    maxPoints = 5000,
    WebSocketImpl = WebSocket,
    initialRetryMs = 1000,
    maxRetryMs = 10_000,
    staleAfterMs = 3000,
  } = options

  const status = ref<ConnectionStatus>('connecting')
  const track = shallowRef<readonly GpsFix[]>([])
  const latest = computed(() => track.value.at(-1) ?? null)
  const lastFixAt = ref<number | null>(null)
  const rateHz = ref(0)
  const clock = ref(Date.now()) // 每秒更新，讓 stale 在資料停了之後也會變
  const stale = computed(
    () => status.value !== 'open' || lastFixAt.value === null || clock.value - lastFixAt.value > staleAfterMs,
  )

  let socket: WebSocket | null = null
  let retryMs = initialRetryMs
  let retryTimer: ReturnType<typeof setTimeout> | undefined
  let disposed = false
  let session: string | null = null
  let lastSeq = 0 // 去重用；seq 只在同一個 session 內有意義
  const arrivals: number[] = []

  function connect() {
    status.value = 'connecting'
    const ws = new WebSocketImpl(url)
    socket = ws
    ws.onopen = () => {
      status.value = 'open'
      retryMs = initialRetryMs
    }
    ws.onmessage = (event: MessageEvent<string>) => handleMessage(JSON.parse(event.data) as ServerMessage)
    // onerror 之後一定會接著 onclose，重連統一在 onclose 處理
    ws.onclose = () => {
      if (socket !== ws) return
      socket = null
      status.value = 'closed'
      if (disposed) return
      retryTimer = setTimeout(connect, retryMs)
      retryMs = Math.min(retryMs * 2, maxRetryMs)
    }
  }

  function handleMessage(message: ServerMessage) {
    if (message.type === 'snapshot') {
      const { points } = message
      const sameSession = message.session === session
      // 同一個 session：snapshot 之前的點保留，其餘以 snapshot 為準（補上斷線期間漏掉的點）。
      // 不同 session：舊的航跡全部保留，新 session 的點接在後面
      const firstSeq = points[0]?.seq ?? Infinity
      const kept = sameSession ? track.value.filter((p) => p.seq < firstSeq) : track.value
      track.value = capped([...kept, ...points])
      lastSeq = points.at(-1)?.seq ?? (sameSession ? lastSeq : 0)
      session = message.session
      return
    }
    const fix = message.data
    if (fix.seq <= lastSeq) return // 重複或過期
    lastSeq = fix.seq
    track.value = capped([...track.value, fix])
    const arrivedAt = Date.now()
    lastFixAt.value = arrivedAt
    arrivals.push(arrivedAt)
    updateRate(arrivedAt)
  }

  // 超過上限時一次修掉 10%，地圖才不必每一筆都整條重畫
  function capped(points: GpsFix[]): GpsFix[] {
    return points.length > maxPoints ? points.slice(-Math.floor(maxPoints * 0.9)) : points
  }

  function updateRate(now = Date.now()) {
    while (arrivals.length > 0 && now - arrivals[0]! > RATE_WINDOW_MS) arrivals.shift()
    const last = arrivals.at(-1)
    const span = arrivals.length >= 2 ? last! - arrivals[0]! : 0
    // 過期（同 stale 的門檻）就是 0，不要等舊的點移出視窗，否則會出現「無資料・5 Hz」
    rateHz.value = span > 0 && now - last! <= staleAfterMs ? ((arrivals.length - 1) * 1000) / span : 0
  }

  function clearTrack() {
    track.value = []
  }

  // 資料停了也要讓頻率歸零、讓 stale 成立
  const tickTimer = setInterval(() => {
    clock.value = Date.now()
    updateRate(clock.value)
  }, 1000)
  connect()

  onScopeDispose(() => {
    disposed = true
    clearTimeout(retryTimer)
    clearInterval(tickTimer)
    const ws = socket
    socket = null
    ws?.close()
  })

  return { status, track, latest, lastFixAt, stale, rateHz, clearTrack }
}
