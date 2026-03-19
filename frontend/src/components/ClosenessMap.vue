<template>
  <svg class="map-svg" :viewBox="`0 0 ${svgW} ${svgH}`" :width="svgW" :height="svgH">
    <defs>
      <filter id="cl-glow-center" x="-80%" y="-80%" width="260%" height="260%">
        <feGaussianBlur stdDeviation="10" result="blur" />
        <feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge>
      </filter>
      <radialGradient id="cl-bg-grad" cx="50%" cy="50%" r="60%">
        <stop offset="0%" stop-color="#1a1f3a" />
        <stop offset="100%" stop-color="#0a0c18" />
      </radialGradient>
    </defs>

    <rect width="100%" height="100%" fill="url(#cl-bg-grad)" rx="16" />

    <circle
      v-for="s in stars" :key="s.id"
      :cx="s.x * svgW" :cy="s.y * svgH" :r="s.r"
      :fill="`rgba(255,255,255,${s.o})`"
    />

    <line
      v-for="n in scaledNodes" :key="'cl-edge-'+n.user_id"
      :x1="cx" :y1="cy" :x2="n.px" :y2="n.py"
      :stroke="n.color"
      :stroke-opacity="hoveredId && hoveredId !== n.user_id ? 0.05 : 0.25"
      :stroke-width="hoveredId === n.user_id ? 1.8 : 0.8"
      stroke-linecap="round"
    />

    <g
      v-for="n in scaledNodes" :key="'cl-node-'+n.user_id"
      :transform="`translate(${n.px}, ${n.py}) scale(${hoveredId === n.user_id ? 1.3 : 1})`"
      class="cl-node-group"
      @mouseenter="hoveredId = n.user_id"
      @mouseleave="hoveredId = null"
      @click="goToProfile(n.user_id)"
      style="cursor:pointer"
    >
      <circle r="8" :fill="n.color" :fill-opacity="hoveredId === n.user_id ? 1 : 0.85" />
      <text
        text-anchor="middle" dominant-baseline="central"
        font-size="7" fill="white" font-weight="700" font-family="monospace"
        style="pointer-events:none;user-select:none"
      >{{ initials(n.display_name) }}</text>
    </g>

    <g
      v-if="hoveredNode"
      style="pointer-events: none"
      :transform="`translate(${tooltipX(hoveredNode)}, ${tooltipY(hoveredNode)})`"
    >
      <rect :x="-70" y="-40" width="140" height="36" rx="8" fill="#1e2540" stroke="#ffffff20" stroke-width="1" />
      <text text-anchor="middle" y="-26" font-size="11" fill="white" font-family="monospace" font-weight="600">
        {{ hoveredNode.display_name || 'Unknown' }}
      </text>
    </g>

    <g :transform="`translate(${cx}, ${cy})`">
      <circle r="34" fill="#ffffff" fill-opacity="0.03" filter="url(#cl-glow-center)" class="cl-pulse-node" />
      <circle r="22" fill="#e8f4ff" filter="url(#cl-glow-center)" />
      <circle r="17" fill="#c5e4ff" />
      <text
        text-anchor="middle" dominant-baseline="central"
        font-size="8" fill="#0a1628" font-weight="800" font-family="monospace"
        style="pointer-events:none"
      >YOU</text>
    </g>
  </svg>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'

const props = defineProps({
  rawCoordinates: { type: Array, required: true },
  svgW: { type: Number, default: 800 },
  svgH: { type: Number, default: 560 },
})

const router = useRouter()
const hoveredId = ref(null)

const cx = computed(() => props.svgW / 2)
const cy = computed(() => props.svgH / 2)
const maxRadius = computed(() => Math.min(props.svgW, props.svgH) / 2 - 52)

const stars = Array.from({ length: 130 }, (_, i) => ({
  id: i,
  x: Math.sin(i * 7.3) * 0.5 + 0.5,
  y: Math.cos(i * 3.7) * 0.5 + 0.5,
  r: Math.sin(i) * 0.5 + 0.7,
  o: Math.cos(i * 2.1) * 0.2 + 0.25,
}))

const scaledNodes = computed(() => {
  const others = props.rawCoordinates.filter(c => !(c.x === 0 && c.y === 0))
  if (!others.length) return []
  const magnitudes = others.map(c => Math.sqrt(c.x * c.x + c.y * c.y))
  const maxMag = Math.max(1e-9, ...magnitudes)
  return others.map((c, i) => ({
    ...c,
    px: cx.value + (c.x / maxMag) * maxRadius.value,
    py: cy.value + (c.y / maxMag) * maxRadius.value,
    color: distanceColor(magnitudes[i] / maxMag),
  }))
})

const hoveredNode = computed(() =>
  hoveredId.value ? scaledNodes.value.find(n => n.user_id === hoveredId.value) : null
)

function distanceColor(t) {
  const r = Math.round(96 + (30 - 96) * t)
  const g = Math.round(212 + (58 - 212) * t)
  const b = Math.round(247 + (95 - 247) * t)
  return `rgb(${r},${g},${b})`
}

function initials(name) {
  if (!name) return '?'
  return name.trim().split(/\s+/).map(w => w[0]).join('').toUpperCase().slice(0, 2)
}

function tooltipX(node) { return Math.min(Math.max(node.px, 70), props.svgW - 70) }
function tooltipY(node) { return node.py < 100 ? node.py + 60 : node.py - 60 }
function goToProfile(userId) { router.push(`/profile/${userId}`) }
</script>

<style scoped>
.map-svg {
  width: 100%;
  height: auto;
  border-radius: 16px;
  border: 1px solid #181e38;
  box-shadow:
    0 0 0 1px #0d1124,
    0 0 80px rgba(96, 212, 247, 0.04),
    0 8px 60px rgba(0, 0, 0, 0.7);
  display: block;
}
.cl-node-group {
  transition: transform 0.15s ease;
  transform-box: fill-box;
  transform-origin: center;
}
@keyframes cl-pulse {
  0%, 100% { opacity: 0.18; }
  50% { opacity: 0.06; }
}
.cl-pulse-node { animation: cl-pulse 3.5s ease-in-out infinite; }
</style>
