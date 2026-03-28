<template>
  <svg
    ref="svgEl"
    class="map-svg"
    :viewBox="`0 0 ${svgW} ${svgH}`"
    :width="svgW"
    :height="svgH"
    :style="{ cursor: dragging ? 'grabbing' : 'grab' }"
    @wheel.prevent="onWheel"
    @mousedown="onMouseDown"
    @mousemove="onMouseMove"
    @mouseup="stopDrag"
    @mouseleave="stopDrag"
  >
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

    <!-- Fixed background — not affected by zoom/pan -->
    <rect width="100%" height="100%" fill="url(#cl-bg-grad)" rx="16" />
    <circle
      v-for="s in stars" :key="s.id"
      :cx="s.x * svgW" :cy="s.y * svgH" :r="s.r"
      :fill="`rgba(255,255,255,${s.o})`"
    />

    <!-- Zoomable / pannable layer -->
    <g :transform="`translate(${panX}, ${panY}) scale(${zoom})`">
      <line
        v-for="n in scaledNodes" :key="'cl-edge-'+n.user_id"
        :x1="cx" :y1="cy" :x2="n.px" :y2="n.py"
        :stroke="n.color"
        :stroke-opacity="hoveredId && hoveredId !== n.user_id ? 0.05 : 0.25"
        :stroke-width="(hoveredId === n.user_id ? 1.8 : 0.8) / zoom"
        stroke-linecap="round"
      />

      <g
        v-for="n in scaledNodes" :key="'cl-node-'+n.user_id"
        :transform="`translate(${n.px}, ${n.py}) scale(${(hoveredId === n.user_id ? 1.3 : 1) / zoom})`"
        class="cl-node-group"
        @mouseenter="hoveredId = n.user_id"
        @mouseleave="hoveredId = null"
        @click.stop="goToProfile(n.user_id)"
        style="cursor:pointer"
      >
        <circle r="17" :fill="n.color" :fill-opacity="hoveredId === n.user_id ? 1 : 0.85" />
        <text
          text-anchor="middle" dominant-baseline="central"
          font-size="7" fill="white" font-weight="700" font-family="monospace"
          style="pointer-events:none;user-select:none"
        >{{ n.display_name?.length > 4 ? n.display_name.slice(0, 4) + '…' : n.display_name }}</text>
      </g>

      <!-- YOU — position follows zoom/pan but size stays constant -->
      <g :transform="`translate(${cx}, ${cy}) scale(${1 / zoom})`">
        <circle r="34" fill="#ffffff" fill-opacity="0.03" filter="url(#cl-glow-center)" class="cl-pulse-node" />
        <circle r="22" fill="#e8f4ff" filter="url(#cl-glow-center)" />
        <circle r="17" fill="#c5e4ff" />
        <text
          text-anchor="middle" dominant-baseline="central"
          font-size="8" fill="#0a1628" font-weight="800" font-family="monospace"
          style="pointer-events:none"
        >YOU</text>
      </g>
      <!-- Tooltip — rendered last so it's always on top of nodes and YOU -->
      <g
        v-if="hoveredNode"
        style="pointer-events: none"
        :transform="`translate(${tooltipX(hoveredNode)}, ${tooltipY(hoveredNode)}) scale(${1 / zoom})`"
      >
        <rect :x="-60" y="-42" width="120" height="34" rx="7" fill="#1e2540" stroke="#ffffff20" stroke-width="1" />
        <text text-anchor="middle" y="-27" font-size="11" fill="white" font-family="monospace" font-weight="600">
          {{ hoveredNode.display_name || 'Unknown' }}
        </text>
        <text text-anchor="middle" y="-14" font-size="9" :fill="hoveredNode.color" font-family="monospace">
          Tier {{ hoveredNode.tier }}
        </text>
      </g>
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
  computedAt: { type: String, default: null },
})

const router = useRouter()
const svgEl = ref(null)
const hoveredId = ref(null)

// Zoom / pan state
const zoom = ref(1)
const panX = ref(0)
const panY = ref(0)
const dragging = ref(false)
const wasDragging = ref(false)
const dragOrigin = ref({ x: 0, y: 0, px: 0, py: 0 })

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
  const clusterColors = computeClusterColors(others)
  return others.map((c, i) => ({
    ...c,
    px: cx.value + (c.x / maxMag) * maxRadius.value,
    py: cy.value + (c.y / maxMag) * maxRadius.value,
    color: clusterColors[c.user_id] ?? CLUSTER_PALETTE[0],
  }))
})

const hoveredNode = computed(() =>
  hoveredId.value ? scaledNodes.value.find(n => n.user_id === hoveredId.value) : null
)

const CLUSTER_PALETTE = [
  '#60d4f7', '#a78bfa', '#34d399', '#fbbf24',
  '#f87171', '#fb923c', '#e879f9', '#4ade80',
  '#38bdf8', '#c084fc', '#86efac', '#fde68a',
]

function computeClusterColors(nodes) {
  if (!nodes.length) return {}

  // Adaptive epsilon: median nearest-neighbor distance × 2.
  // Scales automatically to whatever spread the t-SNE produced.
  const nnDists = nodes.map(n => {
    let min = Infinity
    for (const m of nodes) {
      if (m.user_id === n.user_id) continue
      const d = (n.x - m.x) ** 2 + (n.y - m.y) ** 2
      if (d < min) min = d
    }
    return Math.sqrt(min)
  }).sort((a, b) => a - b)
  const eps = nnDists[Math.floor(nnDists.length / 2)] * 3
  const minPts = 2

  // DBSCAN — finds clusters by density, no k needed
  const labels = {}   // user_id → cluster index, or -1 for noise
  const visited = new Set()
  let clusterIdx = 0

  const neighbors = n => nodes.filter(m =>
    m.user_id !== n.user_id &&
    (n.x - m.x) ** 2 + (n.y - m.y) ** 2 <= eps * eps
  )

  for (const node of nodes) {
    if (visited.has(node.user_id)) continue
    visited.add(node.user_id)
    const nbrs = neighbors(node)
    if (nbrs.length < minPts) { labels[node.user_id] = -1; continue }

    labels[node.user_id] = clusterIdx
    const queue = nbrs.filter(n => !visited.has(n.user_id))
    while (queue.length) {
      const curr = queue.shift()
      if (visited.has(curr.user_id)) { if (labels[curr.user_id] === -1) labels[curr.user_id] = clusterIdx; continue }
      visited.add(curr.user_id)
      labels[curr.user_id] = clusterIdx
      const currNbrs = neighbors(curr)
      if (currNbrs.length >= minPts) queue.push(...currNbrs.filter(n => !visited.has(n.user_id)))
    }
    clusterIdx++
  }

  // Noise points (-1): inherit color of their nearest cluster member
  const colors = {}
  for (const n of nodes) {
    if (labels[n.user_id] !== -1) { colors[n.user_id] = CLUSTER_PALETTE[labels[n.user_id] % CLUSTER_PALETTE.length]; continue }
    let minD = Infinity, best = 0
    for (const m of nodes) {
      if (labels[m.user_id] === -1) continue
      const d = (n.x - m.x) ** 2 + (n.y - m.y) ** 2
      if (d < minD) { minD = d; best = labels[m.user_id] }
    }
    colors[n.user_id] = CLUSTER_PALETTE[best % CLUSTER_PALETTE.length]
  }
  return colors
}

function initials(name) {
  if (!name) return '?'
  return name.trim().split(/\s+/).map(w => w[0]).join('').toUpperCase().slice(0, 2)
}

function tooltipX(node) { return node.px }
function tooltipY(node) { return node.py - 25 / zoom.value }

function goToProfile(userId) {
  if (wasDragging.value) return
  router.push(`/profile/${userId}`)
}

// Convert screen coords to SVG coordinate space
function screenToSvg(clientX, clientY) {
  const rect = svgEl.value.getBoundingClientRect()
  const scaleX = props.svgW / rect.width
  const scaleY = props.svgH / rect.height
  return {
    x: (clientX - rect.left) * scaleX,
    y: (clientY - rect.top) * scaleY,
  }
}

function onWheel(e) {
  const factor = e.deltaY < 0 ? 1.2 : 1 / 1.2
  const newZoom = Math.max(0.3, Math.min(50, zoom.value * factor))
  const { x, y } = screenToSvg(e.clientX, e.clientY)
  panX.value = x - (x - panX.value) * (newZoom / zoom.value)
  panY.value = y - (y - panY.value) * (newZoom / zoom.value)
  zoom.value = newZoom
}

function onMouseDown(e) {
  dragging.value = true
  wasDragging.value = false
  dragOrigin.value = { x: e.clientX, y: e.clientY, px: panX.value, py: panY.value }
}

function onMouseMove(e) {
  if (!dragging.value) return
  const dx = e.clientX - dragOrigin.value.x
  const dy = e.clientY - dragOrigin.value.y
  if (Math.abs(dx) > 3 || Math.abs(dy) > 3) wasDragging.value = true
  const rect = svgEl.value.getBoundingClientRect()
  const scaleX = props.svgW / rect.width
  const scaleY = props.svgH / rect.height
  panX.value = dragOrigin.value.px + dx * scaleX
  panY.value = dragOrigin.value.py + dy * scaleY
}

function stopDrag() {
  dragging.value = false
  // Reset wasDragging after a tick so click handler can read it first
  setTimeout(() => { wasDragging.value = false }, 0)
}
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
  user-select: none;
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
