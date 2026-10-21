<script setup lang="ts">
import L from 'leaflet'
import { onBeforeUnmount, onMounted, useTemplateRef, watch } from 'vue'

import type { AppConfig } from '../config'
import type { GpsFix } from '../types'

const props = defineProps<{
  config: AppConfig
  track: readonly GpsFix[]
  course: number | null // 船頭方向（度）；null 時維持上一次的方向
}>()
const follow = defineModel<boolean>('follow', { required: true })

const DEFAULT_CENTER: L.LatLngTuple = [24.5915, 121.8725] // 蘇澳港中央港池
const container = useTemplateRef<HTMLDivElement>('container')

// Leaflet 物件不放進 Vue 的 reactivity，避免被包成 Proxy 拖慢效能
let map: L.Map | undefined
let trail: L.Polyline | undefined
let vessel: L.Marker | undefined
let drawnFirstSeq: number | null = null
let drawnCount = 0
let heading = 0

const vesselIcon = L.divIcon({
  className: 'vessel-icon',
  html: `<svg class="vessel" viewBox="0 0 32 32" width="32" height="32" aria-hidden="true">
           <path d="M16 3 L23 26 L16 21 L9 26 Z" />
         </svg>`,
  iconSize: [32, 32],
  iconAnchor: [16, 16],
})

onMounted(() => {
  map = L.map(container.value!, { center: DEFAULT_CENTER, zoom: 15 })
  L.tileLayer(props.config.tileUrl, { maxZoom: 19, attribution: props.config.tileAttribution }).addTo(map)
  trail = L.polyline([], { color: '#e4572e', weight: 3, opacity: 0.85 }).addTo(map)
  vessel = L.marker(DEFAULT_CENTER, { icon: vesselIcon, interactive: false, keyboard: false })
  map.on('dragstart', () => (follow.value = false)) // 使用者自己拖地圖，就不再自動跟隨
  render(props.track)
})

onBeforeUnmount(() => {
  map?.remove()
  map = undefined
})

watch(() => props.track, render)
watch(follow, (on) => {
  const last = props.track.at(-1)
  if (on && map && last) map.panTo([last.lat, last.lon])
})

function render(track: readonly GpsFix[]) {
  if (!map || !trail || !vessel) return

  // 只是在尾端多了幾點 → addLatLng 增量畫；換了 snapshot、清除或修剪過 → 整條重畫
  const firstSeq = track[0]?.seq ?? null
  if (firstSeq !== null && firstSeq === drawnFirstSeq && track.length >= drawnCount) {
    for (const p of track.slice(drawnCount)) trail.addLatLng([p.lat, p.lon])
  } else {
    trail.setLatLngs(track.map((p): L.LatLngTuple => [p.lat, p.lon]))
  }
  drawnFirstSeq = firstSeq
  drawnCount = track.length

  const last = track.at(-1)
  if (!last) {
    vessel.remove()
    return
  }
  vessel.setLatLng([last.lat, last.lon])
  if (!map.hasLayer(vessel)) vessel.addTo(map)
  if (props.course !== null) heading = props.course
  const icon = vessel.getElement()?.querySelector<SVGElement>('.vessel')
  if (icon) icon.style.transform = `rotate(${heading}deg)`
  if (follow.value) map.panTo([last.lat, last.lon], { animate: true, duration: 0.25 })
}

/** 縮放到整條軌跡，並關閉跟隨 */
function fitTrack() {
  if (!map || !trail || drawnCount === 0) return
  follow.value = false
  map.fitBounds(trail.getBounds(), { padding: [48, 48] })
}

defineExpose({ fitTrack })
</script>

<template>
  <div ref="container" class="track-map" role="application" aria-label="即時航跡地圖" />
</template>

<style scoped>
.track-map {
  height: 100%;
  width: 100%;
}

.track-map :deep(.vessel-icon) {
  background: none;
  border: none;
}

.track-map :deep(.vessel) {
  fill: #e4572e;
  stroke: #fff;
  stroke-width: 2;
  transform-origin: 50% 50%;
  transition: transform 0.2s linear;
  filter: drop-shadow(0 1px 2px rgb(0 0 0 / 0.45));
}
</style>
