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
        :x1="youPx" :y1="youPy" :x2="n.px" :y2="n.py"
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
      <g :transform="`translate(${youPx}, ${youPy}) scale(${1 / zoom})`">
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
import { ref, computed, watch } from 'vue'
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

const PAD = 60

// YOU position in SVG space (set by scaledNodes, read by template)
const youPx = ref(0)
const youPy = ref(0)

// Star field generated once using deterministic math (so stable across renders)
const stars = Array.from({ length: 130 }, (_, i) => ({
  id: i,
  x: Math.sin(i * 7.3) * 0.5 + 0.5,
  y: Math.cos(i * 3.7) * 0.5 + 0.5,
  r: Math.sin(i) * 0.5 + 0.7,
  o: Math.cos(i * 2.1) * 0.2 + 0.25,
}))

/*
  Converts raw t-SNE coordinates into screen positions, scaled to fit within maxRadius
  Also assigns each node a color based on its cluster (computed with DBSCAN)
*/
const scaledNodes = computed(() => {
  // Closeness map shows tier 1 (Inner Circle) and tier 2 (2nd Degree) only.
  // Tier 3 is excluded — DBSCAN is O(n²) and 3rd-degree sets can be 1000+ nodes.
  const others = props.rawCoordinates.filter(c => !(c.x === 0 && c.y === 0) && c.tier <= 2)
  if (!others.length) return []

  // Normalize friends using uniform scale (same for X and Y) so the UMAP shape
  // is preserved — independent axis scaling distorts clusters into rows/columns
  // when one axis has outliers that expand its range far beyond the other.
  const minX = Math.min(...others.map(c => c.x))
  const maxX = Math.max(...others.map(c => c.x))
  const minY = Math.min(...others.map(c => c.y))
  const maxY = Math.max(...others.map(c => c.y))
  const usableW = props.svgW - PAD * 2
  const usableH = props.svgH - PAD * 2
  // Pick a single scale so the larger axis fills its dimension
  const scaleX = usableW / (maxX - minX || 1)
  const scaleY = usableH / (maxY - minY || 1)
  const scale = Math.min(scaleX, scaleY)
  // Center the scaled content in the canvas
  const offsetX = PAD + (usableW - (maxX - minX) * scale) / 2
  const offsetY = PAD + (usableH - (maxY - minY) * scale) / 2

  const toSvg = (x, y) => ({
    px: offsetX + (x - minX) * scale,
    py: offsetY + (y - minY) * scale,
  })

  // Place YOU at the center of the canvas.
  youPx.value = props.svgW / 2
  youPy.value = props.svgH / 2

  const projected = others.map(c => ({ ...c, ...toSvg(c.x, c.y) }))
  const clusterColors = computeClusterColors(projected)
  return projected.map(c => ({ ...c, color: clusterColors[c.user_id] ?? CLUSTER_PALETTE[0] }))
})

const hoveredNode = computed(() =>
  hoveredId.value ? scaledNodes.value.find(n => n.user_id === hoveredId.value) : null
)

// 12-color palette cycled through cluster indices
const CLUSTER_PALETTE = [
  '#60d4f7', '#a78bfa', '#34d399', '#fbbf24',
  '#f87171', '#fb923c', '#e879f9', '#4ade80',
  '#38bdf8', '#c084fc', '#86efac', '#fde68a',
]

/*
  K-means clustering on SVG pixel positions.
  Always produces k distinct color groups — works even when nodes are uniformly
  spread and DBSCAN would merge everything into one cluster.
  k = ceil(sqrt(n / 2)), capped at palette size.
*/
function computeClusterColors(nodes) {
  if (!nodes.length) return {}
  const k = Math.min(Math.ceil(Math.sqrt(nodes.length / 2)), CLUSTER_PALETTE.length)

  // k-means++ init: first centroid = node farthest from canvas center,
  // each next centroid = node with max distance to nearest existing centroid.
  // Deterministic — no randomness.
  const canvasCx = nodes.reduce((s, n) => s + n.px, 0) / nodes.length
  const canvasCy = nodes.reduce((s, n) => s + n.py, 0) / nodes.length
  let centroids = []
  // Seed: node farthest from centroid of all nodes
  centroids.push((() => {
    let best = nodes[0], bestD = 0
    for (const n of nodes) {
      const d = (n.px - canvasCx) ** 2 + (n.py - canvasCy) ** 2
      if (d > bestD) { bestD = d; best = n }
    }
    return { px: best.px, py: best.py }
  })())
  // Subsequent centroids: node with max min-distance to any existing centroid
  while (centroids.length < k) {
    let best = nodes[0], bestD = 0
    for (const n of nodes) {
      const minD = Math.min(...centroids.map(c => (n.px - c.px) ** 2 + (n.py - c.py) ** 2))
      if (minD > bestD) { bestD = minD; best = n }
    }
    centroids.push({ px: best.px, py: best.py })
  }

  let labels = new Array(nodes.length).fill(0)
  for (let iter = 0; iter < 30; iter++) {
    // Assign each node to nearest centroid
    const next = nodes.map(n => {
      let best = 0, bestD = Infinity
      for (let c = 0; c < k; c++) {
        const d = (n.px - centroids[c].px) ** 2 + (n.py - centroids[c].py) ** 2
        if (d < bestD) { bestD = d; best = c }
      }
      return best
    })
    // Update centroids
    const sums = Array.from({ length: k }, () => ({ px: 0, py: 0, count: 0 }))
    next.forEach((c, i) => { sums[c].px += nodes[i].px; sums[c].py += nodes[i].py; sums[c].count++ })
    centroids = sums.map((s, c) => s.count ? { px: s.px / s.count, py: s.py / s.count } : centroids[c])
    if (next.every((v, i) => v === labels[i])) break
    labels = next
  }

  const colors = {}
  nodes.forEach((n, i) => { colors[n.user_id] = CLUSTER_PALETTE[labels[i] % CLUSTER_PALETTE.length] })
  return colors
}

// Positions tooltip above the hovered node, adjusted for current zoom level
function tooltipX(node) { return node.px }
function tooltipY(node) { return node.py - (25 + 17) / zoom.value }

/*
  Prevents click from firing after a drag (wasDragging is set during mousemove
  and cleared after a tick so this handler can read it before it resets)
*/
function goToProfile(userId) {
  if (wasDragging.value) return
  router.push(`/profile/${userId}`)
}

// Converts screen pixel coordinates to SVG coordinate space, accounting for element scaling
function screenToSvg(clientX, clientY) {
  const rect = svgEl.value.getBoundingClientRect()
  const scaleX = props.svgW / rect.width
  const scaleY = props.svgH / rect.height
  return {
    x: (clientX - rect.left) * scaleX,
    y: (clientY - rect.top) * scaleY,
  }
}

/*
  Zooms toward the cursor position by adjusting pan so the point under
  the cursor stays fixed as zoom changes
*/
function onWheel(e) {
  const factor = e.deltaY < 0 ? 1.05 : 1 / 1.05
  const newZoom = Math.max(0.3, Math.min(50, zoom.value * factor))
  const { x, y } = screenToSvg(e.clientX, e.clientY)
  panX.value = x - (x - panX.value) * (newZoom / zoom.value)
  panY.value = y - (y - panY.value) * (newZoom / zoom.value)
  zoom.value = newZoom
}

// Records drag start position
function onMouseDown(e) {
  dragging.value = true
  wasDragging.value = false
  dragOrigin.value = { x: e.clientX, y: e.clientY, px: panX.value, py: panY.value }
}

// Translates mouse delta into pan offset
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

// Ends drag and resets wasDragging after a tick
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
