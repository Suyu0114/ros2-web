<script setup lang="ts">
import { computed, onBeforeUnmount, ref } from 'vue'

import { formatDms, type Motion } from '../lib/geo'
import type { ConnectionStatus, GpsFix } from '../types'

const props = defineProps<{
  status: ConnectionStatus
  latest: GpsFix | null
  motion: Motion | null
  rateHz: number
  points: number
  lastFixAt: number | null
  stale: boolean
}>()
const follow = defineModel<boolean>('follow', { required: true })
const emit = defineEmits<{ fit: []; clear: [] }>()

// 每秒更新一次「多久前收到」
const now = ref(Date.now())
const ticker = setInterval(() => (now.value = Date.now()), 1000)
onBeforeUnmount(() => clearInterval(ticker))

const ageS = computed(() => (props.lastFixAt === null ? null : Math.max(0, (now.value - props.lastFixAt) / 1000)))

const link = computed(() => {
  if (props.status === 'connecting') return { label: '連線中…', tone: 'warn' }
  if (props.status === 'closed') return { label: '已斷線，重新連線中', tone: 'bad' }
  if (props.stale) return { label: '已連線・無資料', tone: 'warn' }
  return { label: '已連線', tone: 'ok' }
})

// 海事與軍方通聯慣用 UTC，不用瀏覽器的時區
const gpsTime = computed(() => (props.latest ? new Date(props.latest.t).toISOString().slice(11, 19) : '—'))
</script>

<template>
  <section class="panel" aria-label="遙測資訊">
    <header>
      <h1>USV 即時航跡</h1>
      <span class="link" :class="link.tone" role="status">{{ link.label }}</span>
    </header>

    <dl>
      <div>
        <dt>緯度</dt>
        <dd v-if="latest">
          {{ latest.lat.toFixed(6) }}°<small>{{ formatDms(latest.lat, 'lat') }}</small>
        </dd>
        <dd v-else>—</dd>
      </div>
      <div>
        <dt>經度</dt>
        <dd v-if="latest">
          {{ latest.lon.toFixed(6) }}°<small>{{ formatDms(latest.lon, 'lon') }}</small>
        </dd>
        <dd v-else>—</dd>
      </div>
      <div>
        <dt>航速 SOG</dt>
        <dd>{{ motion ? `${motion.speedKnots.toFixed(1)} kn` : '—' }}</dd>
      </div>
      <div>
        <dt>航向 COG</dt>
        <dd>{{ motion?.courseDeg != null ? `${motion.courseDeg.toFixed(0).padStart(3, '0')}°` : '—' }}</dd>
      </div>
      <div>
        <dt>GPS 時間 UTC</dt>
        <dd>{{ gpsTime }}</dd>
      </div>
      <div>
        <dt>更新頻率</dt>
        <dd>{{ rateHz.toFixed(1) }} Hz</dd>
      </div>
      <div>
        <dt>軌跡點數</dt>
        <dd>{{ points.toLocaleString('zh-TW') }}</dd>
      </div>
      <div>
        <dt>最後更新</dt>
        <dd>{{ ageS === null ? '—' : `${ageS.toFixed(0)} 秒前` }}</dd>
      </div>
    </dl>

    <div class="actions">
      <button type="button" :aria-pressed="follow" :class="{ active: follow }" @click="follow = !follow">
        跟隨
      </button>
      <button type="button" :disabled="points === 0" @click="emit('fit')">全覽</button>
      <button type="button" :disabled="points === 0" @click="emit('clear')">清除軌跡</button>
    </div>
  </section>
</template>

<style scoped>
.panel {
  background: var(--panel-bg);
  color: var(--text);
  border-radius: 10px;
  box-shadow: 0 4px 16px rgb(0 0 0 / 0.2);
  padding: 12px 14px;
  backdrop-filter: blur(4px);
}

header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 8px;
}

h1 {
  font-size: 1rem;
  margin: 0;
}

.link {
  font-size: 0.75rem;
  font-weight: 600;
  padding: 2px 8px;
  border-radius: 999px;
  color: #fff;
  white-space: nowrap;
}
.link.ok {
  background: var(--ok);
}
.link.warn {
  background: var(--warn);
}
.link.bad {
  background: var(--bad);
}

dl {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 6px 12px;
  margin: 0;
}

dt {
  font-size: 0.7rem;
  color: var(--muted);
}

dd {
  margin: 0;
  font-variant-numeric: tabular-nums;
  font-size: 0.95rem;
}

dd small {
  display: block;
  font-size: 0.7rem;
  color: var(--muted);
}

.actions {
  display: flex;
  gap: 6px;
  margin-top: 10px;
}

button {
  flex: 1;
  font: inherit;
  font-size: 0.8rem;
  padding: 6px 0;
  border-radius: 6px;
  border: 1px solid var(--border);
  background: transparent;
  color: var(--text);
  cursor: pointer;
}
button.active {
  background: var(--accent);
  border-color: var(--accent);
  color: #fff;
}
button:disabled {
  opacity: 0.45;
  cursor: default;
}
</style>
