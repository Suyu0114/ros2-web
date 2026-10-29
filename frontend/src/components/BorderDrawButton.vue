<script setup lang="ts">
// 依序畫出的四條邊：上往右 → 右往下 → 下往左 → 左往上
const EDGES = ['top', 'right', 'bottom', 'left'] as const
</script>

<template>
  <button type="button" class="draw-btn">
    <slot />
    <span v-for="edge in EDGES" :key="edge" class="edge" :class="edge" aria-hidden="true" />
  </button>
</template>

<style scoped>
.draw-btn {
  --seg: 0.18s;
  position: relative;
  font: inherit;
  font-size: 0.8rem;
  padding: 6px 0;
  border: 1px solid var(--border);
  border-radius: 0; /* 直角，四條線才接得整齊 */
  background: transparent;
  color: var(--muted); /* 不用 --text：淺色主題的 --text 與 --accent 同為海軍藍，hover 時看不出換色 */
  cursor: pointer;
  /* 移出：文字先換回，邊再依反向順序收回 */
  transition:
    color var(--seg) ease,
    background-color var(--seg) ease;
}

.edge {
  position: absolute;
  background: var(--accent);
  pointer-events: none;
  transition: transform var(--seg) linear var(--out);
}
/* 收回時沿用同一個 transform-origin，方向自然與畫出時相反 */
.edge.top {
  --in: 0s;
  --out: calc(var(--seg) * 4);
  top: -1px;
  left: -1px;
  right: -1px;
  height: 2px;
  transform: scaleX(0);
  transform-origin: left;
}
.edge.right {
  --in: var(--seg);
  --out: calc(var(--seg) * 3);
  top: -1px;
  right: -1px;
  bottom: -1px;
  width: 2px;
  transform: scaleY(0);
  transform-origin: top;
}
.edge.bottom {
  --in: calc(var(--seg) * 2);
  --out: calc(var(--seg) * 2);
  bottom: -1px;
  left: -1px;
  right: -1px;
  height: 2px;
  transform: scaleX(0);
  transform-origin: right;
}
.edge.left {
  --in: calc(var(--seg) * 3);
  --out: var(--seg);
  top: -1px;
  left: -1px;
  bottom: -1px;
  width: 2px;
  transform: scaleY(0);
  transform-origin: bottom;
}

/* 只在真的能 hover 的裝置上觸發：手機點按後 hover 會黏住，關掉「跟隨」後看起來仍像開著 */
@media (hover: hover) {
  .draw-btn:not(:disabled):hover {
    color: var(--accent);
    transition-delay: calc(var(--seg) * 4), 0s; /* 文字等邊畫完才換色；底色即時，點按才有回饋 */
  }
  .draw-btn:not(:disabled):hover .edge {
    transform: none;
    transition-delay: var(--in);
  }
}

.draw-btn:focus-visible,
.draw-btn.active {
  color: var(--accent);
  transition-delay: calc(var(--seg) * 4), 0s;
}
.draw-btn:focus-visible .edge,
.draw-btn.active .edge {
  transform: none;
  transition-delay: var(--in);
}
.draw-btn.active {
  background: var(--accent-tint);
}

.draw-btn:disabled {
  opacity: 0.45;
  cursor: default;
}

/* 所有 delay 都是 --seg 的倍數，歸零後一起變成即時切換 */
@media (prefers-reduced-motion: reduce) {
  .draw-btn {
    --seg: 0s;
  }
}
</style>
