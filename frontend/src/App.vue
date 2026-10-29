<script setup lang="ts">
import { computed, ref, useTemplateRef } from 'vue'

import TelemetryPanel from './components/TelemetryPanel.vue'
import TrackMap from './components/TrackMap.vue'
import { useGpsStream } from './composables/useGpsStream'
import type { AppConfig } from './config'
import { estimateMotion } from './lib/geo'

defineProps<{ config: AppConfig }>()

const { status, track, latest, lastFixAt, stale, rateHz, clearTrack } = useGpsStream()
const motion = computed(() => estimateMotion(track.value))
const follow = ref(true)
const trackMap = useTemplateRef<InstanceType<typeof TrackMap>>('trackMap')
</script>

<template>
  <main class="layout">
    <TrackMap
      ref="trackMap"
      v-model:follow="follow"
      class="map"
      :config="config"
      :track="track"
      :course="motion?.courseDeg ?? null"
      :stale="stale"
    />
    <TelemetryPanel
      v-model:follow="follow"
      class="telemetry"
      :status="status"
      :latest="latest"
      :motion="motion"
      :rate-hz="rateHz"
      :points="track.length"
      :last-fix-at="lastFixAt"
      :stale="stale"
      @fit="trackMap?.fitTrack()"
      @clear="clearTrack"
    />
  </main>
</template>

<style scoped>
.layout {
  position: relative;
  height: 100%;
}

.map {
  position: absolute;
  inset: 0;
}

.telemetry {
  position: absolute;
  top: 12px;
  right: 12px;
  z-index: 1000; /* 高於 Leaflet 的圖層 */
  width: min(340px, calc(100% - 24px));
}

/* 手機：面板移到下方，不擋左上角的縮放按鈕；留出右下角的圖資歸屬標示 */
@media (max-width: 600px) {
  .telemetry {
    top: auto;
    bottom: 24px;
    right: 8px;
    left: 8px;
    width: auto;
  }
}
</style>
