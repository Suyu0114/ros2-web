import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { effectScope } from 'vue'

import type { GpsFix, ServerMessage } from '../types'
import { defaultStreamUrl, useGpsStream } from './useGpsStream'

class FakeWebSocket {
  static instances: FakeWebSocket[] = []
  onopen: (() => void) | null = null
  onmessage: ((event: { data: string }) => void) | null = null
  onclose: (() => void) | null = null
  closed = false

  constructor(public url: string) {
    FakeWebSocket.instances.push(this)
  }

  close() {
    this.closed = true
    this.onclose?.()
  }

  // 測試用：模擬伺服器行為
  serverOpen() {
    this.onopen?.()
  }
  serverSend(message: ServerMessage) {
    this.onmessage?.({ data: JSON.stringify(message) })
  }
  serverDrop() {
    this.onclose?.()
  }
}

const fix = (seq: number): GpsFix => ({
  seq,
  t: seq * 200,
  lat: 22.6166,
  lon: 120.279 + seq * 1e-5,
  alt: 0,
  status: 0,
  frame_id: 'gps',
})

function setup(options: { maxPoints?: number } = {}) {
  const scope = effectScope()
  const stream = scope.run(() =>
    useGpsStream({
      url: 'ws://test/ws/gps',
      WebSocketImpl: FakeWebSocket as unknown as new (url: string) => WebSocket,
      ...options,
    }),
  )!
  const socket = () => FakeWebSocket.instances.at(-1)!
  return { stream, socket, scope }
}

beforeEach(() => {
  FakeWebSocket.instances = []
  vi.useFakeTimers()
})

afterEach(() => {
  vi.useRealTimers()
})

describe('useGpsStream', () => {
  it('replaces the track with the snapshot, then appends live fixes and ignores duplicates', () => {
    const { stream, socket } = setup()
    expect(socket().url).toBe('ws://test/ws/gps')
    expect(stream.status.value).toBe('connecting')

    socket().serverOpen()
    socket().serverSend({ type: 'snapshot', session: 'A', points: [fix(1), fix(2)] })
    socket().serverSend({ type: 'fix', data: fix(3) })
    socket().serverSend({ type: 'fix', data: fix(3) })
    socket().serverSend({ type: 'fix', data: fix(2) })

    expect(stream.status.value).toBe('open')
    expect(stream.track.value.map((f) => f.seq)).toEqual([1, 2, 3])
    expect(stream.latest.value?.seq).toBe(3)
  })

  it('creates a new track array on every update so watchers fire', () => {
    const { stream, socket } = setup()
    socket().serverSend({ type: 'snapshot', session: 'A', points: [fix(1)] })
    const before = stream.track.value
    socket().serverSend({ type: 'fix', data: fix(2) })
    expect(stream.track.value).not.toBe(before)
  })

  it('trims 10% at once when exceeding maxPoints', () => {
    const { stream, socket } = setup({ maxPoints: 10 })
    socket().serverSend({ type: 'snapshot', session: 'A', points: Array.from({ length: 10 }, (_, i) => fix(i + 1)) })
    socket().serverSend({ type: 'fix', data: fix(11) })
    expect(stream.track.value.map((f) => f.seq)).toEqual([3, 4, 5, 6, 7, 8, 9, 10, 11])
  })

  it('after reconnecting to the same backend, fills the gap from the snapshot without duplicates', () => {
    const { stream, socket } = setup()
    socket().serverSend({ type: 'snapshot', session: 'A', points: [fix(1), fix(2)] })
    socket().serverDrop()
    vi.advanceTimersByTime(1000)
    // 斷線期間 backend 又收到了 3、4
    socket().serverSend({ type: 'snapshot', session: 'A', points: [fix(2), fix(3), fix(4)] })
    socket().serverSend({ type: 'fix', data: fix(4) })
    socket().serverSend({ type: 'fix', data: fix(5) })
    expect(stream.track.value.map((f) => f.seq)).toEqual([1, 2, 3, 4, 5])
  })

  it('keeps the drawn track when the backend restarted and numbers seq from 1 again', () => {
    const { stream, socket } = setup()
    socket().serverSend({ type: 'snapshot', session: 'A', points: [fix(10), fix(11)] })
    socket().serverDrop()
    vi.advanceTimersByTime(1000)
    socket().serverSend({ type: 'snapshot', session: 'B', points: [] })
    socket().serverSend({ type: 'fix', data: fix(1) })
    socket().serverSend({ type: 'fix', data: fix(2) })
    expect(stream.track.value.map((f) => f.seq)).toEqual([10, 11, 1, 2])
  })

  it('reconnects with exponential backoff and resets the delay after a successful open', () => {
    const { stream, socket } = setup()
    socket().serverDrop()
    expect(stream.status.value).toBe('closed')

    vi.advanceTimersByTime(999)
    expect(FakeWebSocket.instances).toHaveLength(1)
    vi.advanceTimersByTime(1)
    expect(FakeWebSocket.instances).toHaveLength(2)
    expect(stream.status.value).toBe('connecting')

    socket().serverDrop()
    vi.advanceTimersByTime(1999)
    expect(FakeWebSocket.instances).toHaveLength(2)
    vi.advanceTimersByTime(1)
    expect(FakeWebSocket.instances).toHaveLength(3)

    socket().serverOpen()
    socket().serverDrop()
    vi.advanceTimersByTime(1000)
    expect(FakeWebSocket.instances).toHaveLength(4)
  })

  it('measures the update rate and decays to zero when data stops', () => {
    const { stream, socket } = setup()
    socket().serverSend({ type: 'snapshot', session: 'A', points: [] })
    for (let seq = 1; seq <= 11; seq++) {
      socket().serverSend({ type: 'fix', data: fix(seq) })
      vi.advanceTimersByTime(200)
    }
    expect(stream.rateHz.value).toBeCloseTo(5, 5)

    // 最後一筆後 3 秒內維持；過期（stale）就歸零，不等舊的點移出 5 秒視窗
    vi.advanceTimersByTime(3000)
    expect(stream.rateHz.value).toBeCloseTo(5, 5)
    vi.advanceTimersByTime(1000)
    expect(stream.rateHz.value).toBe(0)
    expect(stream.stale.value).toBe(true)
  })

  it('marks the position stale until live fixes arrive, when they stop, and while disconnected', () => {
    const { stream, socket } = setup()
    socket().serverOpen()
    socket().serverSend({ type: 'snapshot', session: 'A', points: [fix(1)] })
    expect(stream.stale.value).toBe(true) // snapshot 只是歷史
    expect(stream.lastFixAt.value).toBeNull()

    socket().serverSend({ type: 'fix', data: fix(2) })
    expect(stream.stale.value).toBe(false)
    vi.advanceTimersByTime(3000)
    expect(stream.stale.value).toBe(false)
    vi.advanceTimersByTime(1000)
    expect(stream.stale.value).toBe(true)

    socket().serverSend({ type: 'fix', data: fix(3) })
    expect(stream.stale.value).toBe(false)
    socket().serverDrop()
    expect(stream.stale.value).toBe(true)
  })

  it('closes the socket and stops reconnecting when disposed', () => {
    const { socket, scope } = setup()
    const first = socket()
    scope.stop()
    expect(first.closed).toBe(true)
    vi.advanceTimersByTime(60_000)
    expect(FakeWebSocket.instances).toHaveLength(1)
  })
})

describe('defaultStreamUrl', () => {
  it('uses the page origin and matches the page scheme', () => {
    expect(defaultStreamUrl({ protocol: 'http:', host: 'localhost:8080' })).toBe('ws://localhost:8080/ws/gps')
    expect(defaultStreamUrl({ protocol: 'https:', host: 'gcs.example' })).toBe('wss://gcs.example/ws/gps')
  })
})
