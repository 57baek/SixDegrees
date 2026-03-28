<template>
  <div class="map-wrapper">
    <header class="map-page-header">
      <button @click="router.back()" class="back-btn">← Back</button>
    </header>
    <div class="map-header">
      <h1 class="map-title">People Map</h1>
      <p class="map-subtitle">Your Social Map</p>
      <div class="view-controls">
        <div class="toggle-group">
          <button
            class="toggle-btn"
            :class="{ active: activeView === 'connections' }"
            data-view="connections"
            @click="activeView = 'connections'"
          >Connections</button>
          <button
            class="toggle-btn"
            :class="{ active: activeView === 'closeness' }"
            data-view="closeness"
            @click="activeView = 'closeness'"
          >Closeness</button>
        </div>
        <button v-if="activeView === 'connections'" class="refresh-btn" @click="triggerAndReload" :disabled="loading || triggering">
          <span v-if="triggering" class="spinner" />
          <span v-else>↻</span>
          {{ triggering ? 'Computing…' : 'Refresh Map' }}
        </button>
      </div>
    </div>

    <div class="legend" v-if="activeView === 'connections'">
      <div v-for="t in visibleTiers" :key="t" class="legend-item">
        <span class="legend-dot" :style="{ background: tierColor(t) }" />
        <span>{{ tierLabel(t) }}</span>
      </div>
    </div>

    <div v-if="isMobile" class="mobile-warn">
      ⚠ People Map is best viewed on a larger screen.
    </div>

    <div v-if="loading" class="state-box">
      <div class="loading-ring" />
      <p>Loading your People Map…</p>
    </div>

    <div v-else-if="error" class="state-box">
      <p>Your map hasn't been built yet. Start connecting with others to see your social network come to life.</p>
      <button class="refresh-btn" @click="fetchMap">Retry</button>
    </div>

    <div v-else-if="!rawCoordinates.length" class="state-box">
      <p>No connections yet. Add friends to build your map!</p>
    </div>

    <template v-else>
      <div v-if="activeView === 'connections'" class="canvas-wrap" ref="canvasWrap">
        <svg class="map-svg" :viewBox="`0 0 ${svgW} ${svgH}`" :width="svgW" :height="svgH">
          <defs>
            <filter v-for="t in [0,1,2,3,4]" :key="'f'+t" :id="'glow-'+t" x="-50%" y="-50%" width="200%" height="200%">
              <feGaussianBlur :stdDeviation="t === 0 ? 6 : 3" result="blur" />
              <feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge>
            </filter>
            <filter id="glow-center" x="-80%" y="-80%" width="260%" height="260%">
              <feGaussianBlur stdDeviation="10" result="blur" />
              <feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge>
            </filter>
            <radialGradient id="bg-grad" cx="50%" cy="50%" r="60%">
              <stop offset="0%" stop-color="#1a1f3a" />
              <stop offset="100%" stop-color="#0a0c18" />
            </radialGradient>
          </defs>

          <rect width="100%" height="100%" fill="url(#bg-grad)" rx="16" />

          <circle
            v-for="s in stars" :key="s.id"
            :cx="s.x * svgW" :cy="s.y * svgH" :r="s.r"
            :fill="`rgba(255,255,255,${s.o})`"
          />

          <circle
            v-for="t in visibleTiers" :key="'ring'+t"
            :cx="cx" :cy="cy" :r="ringRadiusForTier(t)"
            fill="none" :stroke="tierColor(t)"
            stroke-opacity="0.08" stroke-dasharray="4 6" stroke-width="1"
          />

          <line
            v-for="n in nodes" :key="'edge-'+n.user_id"
            :x1="cx" :y1="cy" :x2="n.px" :y2="n.py"
            :stroke="tierColor(n.tier)"
            :stroke-opacity="hoveredId && hoveredId !== n.user_id ? 0.05 : 0.28"
            :stroke-width="hoveredId === n.user_id ? 1.8 : 0.8"
            stroke-linecap="round"
          />
          <g
              v-for="n in nodes" :key="'node-'+n.user_id"
              :transform="`translate(${n.px}, ${n.py}) scale(${hoveredId === n.user_id ? 1.3 : 1})`"
              class="node-group"
              @mouseenter="hoveredId = n.user_id"
              @mouseleave="hoveredId = null"
              @click="goToProfile(n.user_id)"
              style="cursor:pointer"
          >
            <circle v-if="n.tier === 0" r="20" :fill="tierColor(0)" fill-opacity="0.12" filter="url(#glow-0)" class="pulse-node" />
            <circle
              :r="nodeRadius(n.tier)"
              :fill="tierColor(n.tier)"
              :fill-opacity="hoveredId === n.user_id ? 1 : 0.85"
              :filter="`url(#glow-${Math.min(n.tier,4)})`"
            />
            <text
              text-anchor="middle" dominant-baseline="central"
              :font-size="n.tier === 0 ? 7 : 6"
              fill="white" font-weight="700" font-family="monospace"
              style="pointer-events:none;user-select:none"
            >{{ n.display_name?.length > 4 ? n.display_name.slice(0, 4) + '…' : n.display_name }}</text>
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
            <text text-anchor="middle" y="-12" font-size="9" :fill="tierColor(hoveredNode.tier)" font-family="monospace">
              {{ tierLabel(hoveredNode.tier) }}
            </text>
          </g>

          <g :transform="`translate(${cx}, ${cy})`">
            <circle r="34" fill="#ffffff" fill-opacity="0.03" filter="url(#glow-center)" class="pulse-node" />
            <circle r="22" fill="#e8f4ff" filter="url(#glow-center)" />
            <circle r="17" fill="#c5e4ff" />
            <text text-anchor="middle" dominant-baseline="central" font-size="8" fill="#0a1628" font-weight="800" font-family="monospace" style="pointer-events:none">YOU</text>
          </g>
        </svg>

        <div class="map-footer">
          <span>{{ nodes.length }} connection{{ nodes.length !== 1 ? 's' : '' }}</span>
          <span v-if="computedAt"> · Updated {{ timeAgo(computedAt) }}</span>
        </div>
      </div>
      <div v-else class="canvas-wrap">
        <ClosenessMap
          :rawCoordinates="closenessCoordinates"
          :svgW="svgW"
          :svgH="svgH"
          :computedAt="closenessComputedAt"
        />
        <div class="map-footer">
          <span>{{ closenessCoordinates.length > 0 ? closenessCoordinates.length - 1 : 0 }} connection{{ (closenessCoordinates.length > 0 ? closenessCoordinates.length - 1 : 0) !== 1 ? 's' : '' }}</span>
          <span v-if="closenessComputedAt"> · Updated {{ timeAgo(closenessComputedAt) }}</span>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { useRouter } from 'vue-router'
import ClosenessMap from '../components/ClosenessMap.vue'
import { supabase } from '../lib/supabase.js'

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const TIER_COLORS = {
  0: '#60d4f7',
  1: '#a78bfa',
  2: '#34d399',
  3: '#fbbf24',
  4: '#f87171',
}
const TIER_LABELS = {
  0: '✦ Inner Circle',
  1: 'Tier 1',
  2: 'Tier 2',
  3: 'Tier 3',
  4: 'Tier 4+',
}

const router = useRouter()
const canvasWrap = ref(null)
const rawCoordinates = ref([])
const computedAt = ref(null)
const closenessCoordinates = ref([])
const closenessComputedAt = ref(null)
const currentUserId = ref(null)
const loading = ref(true)
const triggering = ref(false)
const error = ref(null)
const hoveredId = ref(null)
const activeView = ref('connections')
const svgW = ref(800)
const svgH = ref(560)
const isMobile = ref(false)

const cx = computed(() => svgW.value / 2)
const cy = computed(() => svgH.value / 2)
const maxRadius = computed(() => Math.min(svgW.value, svgH.value) / 2 - 52)

// visibleTiers reads rawCoordinates — not nodes (no circular dep)
const visibleTiers = computed(() =>
  [...new Set(rawCoordinates.value.map(c => Math.min(c.tier ?? 4, 4)))].sort()
)

function ringRadiusForTier(tier) {
  const n = visibleTiers.value.length || 1
  return maxRadius.value * ((Math.min(tier, 4) + 1) / (n + 1))
}

const nodes = computed(() => {
  if (!rawCoordinates.value.length) return []

  const byTier = {}
  for (const c of rawCoordinates.value.filter(c => c.user_id !== currentUserId.value)) {
    const t = Math.min(c.tier ?? 4, 4)
    if (!byTier[t]) byTier[t] = []
    byTier[t].push(c)
  }

  const result = []
  for (const [tierStr, members] of Object.entries(byTier)) {
    const tier = Number(tierStr)
    const ringR = ringRadiusForTier(tier)

    members.forEach((c, i) => {
      let angle
      if (c.x !== undefined && c.y !== undefined && (c.x !== 0 || c.y !== 0)) {
        const baseAngle = Math.atan2(c.y, c.x)
        const spread = (2 * Math.PI) / members.length
        angle = baseAngle + (i - members.length / 2) * spread * 0.35
      } else {
        angle = (2 * Math.PI * i) / members.length - Math.PI / 2
      }

      result.push({
        ...c,
        tier,
        display_name: c.nickname || c.display_name || '',
        px: cx.value + ringR * Math.cos(angle),
        py: cy.value + ringR * Math.sin(angle),
      })
    })
  }
  return result
})

const hoveredNode = computed(() =>
  hoveredId.value ? nodes.value.find(n => n.user_id === hoveredId.value) : null
)

const stars = Array.from({ length: 130 }, (_, i) => ({
  id: i,
  x: (Math.sin(i * 7.3) * 0.5 + 0.5),
  y: (Math.cos(i * 3.7) * 0.5 + 0.5),
  r: (Math.sin(i) * 0.5 + 0.7),
  o: (Math.cos(i * 2.1) * 0.2 + 0.25),
}))

function tierColor(tier) { return TIER_COLORS[Math.min(tier, 4)] ?? TIER_COLORS[4] }
function tierLabel(tier) { return TIER_LABELS[Math.min(tier, 4)] ?? 'Tier 4+' }
function nodeRadius(tier) { return tier === 0 ? 13 : tier === 1 ? 10 : 7 }

function initials(name) {
  if (!name) return '?'
  return name.trim().split(/\s+/).map(w => w[0]).join('').toUpperCase().slice(0, 2)
}
function tooltipX(node) { return Math.min(Math.max(node.px, 70), svgW.value - 70) }
function tooltipY(node) { return node.py < 100 ? node.py + 60 : node.py - 60 }

function timeAgo(iso) {
  if (!iso) return ''
  const mins = Math.floor((Date.now() - new Date(iso).getTime()) / 60000)
  if (mins < 1) return 'just now'
  if (mins < 60) return `${mins}m ago`
  const hrs = Math.floor(mins / 60)
  if (hrs < 24) return `${hrs}h ago`
  return `${Math.floor(hrs / 24)}d ago`
}
function goToProfile(userId) { router.push(`/profile/${userId}`) }

async function fetchMap() {
  loading.value = true
  error.value = null
  try {
    const { data: { user } } = await supabase.auth.getUser()
    const { data: { session } } = await supabase.auth.getSession()
    if (!user || !session) { error.value = 'Not logged in.'; return }
    currentUserId.value = user.id
    const res = await fetch(`${API_BASE}/map/${user.id}`, {
      headers: { Authorization: `Bearer ${session.access_token}` },
    })
    if (res.status === 404) { await triggerAndReload(); return }
    if (!res.ok) throw new Error(`Server error: ${res.status}`)
    const data = await res.json()
    rawCoordinates.value = data.coordinates || []
    computedAt.value = data.computed_at || null
    closenessCoordinates.value = data.coordinates || []
    closenessComputedAt.value = data.computed_at || null
  } catch (e) {
    error.value = e.message || 'Failed to load map.'
  } finally {
    loading.value = false
  }
}

async function triggerAndReload() {
  triggering.value = true
  error.value = null
  try {
    const { data: { user } } = await supabase.auth.getUser()
    const { data: { session } } = await supabase.auth.getSession()
    if (!user || !session) { error.value = 'Not logged in.'; return }
    currentUserId.value = user.id
    const res = await fetch(`${API_BASE}/map/trigger/${user.id}`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${session.access_token}` },
    })
    if (!res.ok) throw new Error(`Trigger failed: ${res.status}`)
    const data = await res.json()
    rawCoordinates.value = data.coordinates || []
    computedAt.value = data.computed_at || null
  } catch (e) {
    error.value = e.message || 'Failed to compute map.'
  } finally {
    triggering.value = false
    loading.value = false
  }
}

function onResize() {
  isMobile.value = window.innerWidth < 600
  if (canvasWrap.value) {
    svgW.value = canvasWrap.value.clientWidth || 800
    svgH.value = Math.max(400, Math.round(svgW.value * 0.65))
  }
}

onMounted(async () => {
  isMobile.value = window.innerWidth < 600
  window.addEventListener('resize', onResize)
  await new Promise(r => setTimeout(r, 0))
  onResize()
  await fetchMap()
})

onBeforeUnmount(() => window.removeEventListener('resize', onResize))
</script>

<style scoped>
@import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=Playfair+Display:wght@600;700&display=swap');

.map-page-header {
  width: 100%;
  max-width: 900px;
  display: flex;
  justify-content: space-between;
  margin-bottom: 2rem;
}

.back-btn {
  padding: 0.5rem 1rem;
  background: #1e2540;
  color: #8090b4;
  border: 1px solid #252b50;
  border-radius: 6px;
  cursor: pointer;
  font-size: 0.95rem;
  font-family: 'DM Mono', monospace;
  transition: all 0.2s;
}

.back-btn:hover {
  border-color: #60d4f7;
  color: #60d4f7;
  background: rgba(96, 212, 247, 0.07);
}

.map-wrapper {
  min-height: 100vh;
  background: #0a0c18;
  color: #e8f0ff;
  font-family: 'DM Mono', monospace;
  padding: 2.5rem 1.5rem 3rem;
  display: flex;
  flex-direction: column;
  align-items: center;
}

.map-header { text-align: center; margin-bottom: 1.6rem; }

.map-title {
  font-family: 'Playfair Display', serif;
  font-size: clamp(2rem, 5vw, 3.2rem);
  font-weight: 700;
  background: #c5e4ff 100%;
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  letter-spacing: -0.02em;
  margin-bottom: 0.35rem;
}

.map-subtitle {
  font-size: 0.76rem;
  color: #6b7a9e;
  letter-spacing: 0.15em;
  text-transform: uppercase;
  margin-bottom: 1.25rem;
}

.refresh-btn {
  display: inline-flex;
  align-items: center;
  gap: 0.45rem;
  padding: 0.5rem 1.25rem;
  border: 1px solid #252b50;
  border-radius: 999px;
  background: transparent;
  color: #8090b4;
  font-family: 'DM Mono', monospace;
  font-size: 0.76rem;
  cursor: pointer;
  transition: border-color 0.2s, color 0.2s, background 0.2s;
  letter-spacing: 0.06em;
}
.refresh-btn:hover:not(:disabled) {
  border-color: #60d4f7;
  color: #60d4f7;
  background: rgba(96, 212, 247, 0.07);
}
.refresh-btn:disabled { opacity: 0.45; cursor: not-allowed; }

.legend {
  display: flex;
  gap: 1.4rem;
  flex-wrap: wrap;
  justify-content: center;
  margin-bottom: 1.2rem;
}
.legend-item {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  font-size: 0.71rem;
  color: #5a6888;
  letter-spacing: 0.06em;
}
.legend-dot { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }

.mobile-warn {
  background: rgba(251, 191, 36, 0.07);
  border: 1px solid rgba(251, 191, 36, 0.22);
  border-radius: 8px;
  color: #fbbf24;
  font-size: 0.73rem;
  padding: 0.55rem 1rem;
  margin-bottom: 1rem;
  max-width: 460px;
  text-align: center;
}

.state-box {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 1.4rem;
  height: 320px;
  color: #40506e;
  font-size: 0.84rem;
  text-align: center;
}
.error-box { color: #f87171; }

.loading-ring {
  width: 40px;
  height: 40px;
  border: 2px solid #1e2540;
  border-top-color: #60d4f7;
  border-radius: 50%;
  animation: spin 0.9s linear infinite;
}

.canvas-wrap {
  width: 100%;
  max-width: 900px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.9rem;
}

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

.node-group {
  transition: transform 0.15s ease;
  transform-box: fill-box;
  transform-origin: center;
}

@keyframes pulse {
  0%, 100% { opacity: 0.18; }
  50% { opacity: 0.06; }
}
.pulse-node { animation: pulse 3.5s ease-in-out infinite; }

.map-footer {
  font-size: 0.7rem;
  color: #313858;
  letter-spacing: 0.07em;
  display: flex;
  gap: 0.6rem;
  align-items: center;
}


.spinner {
  display: inline-block;
  width: 11px;
  height: 11px;
  border: 2px solid #60d4f7;
  border-top-color: transparent;
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

.view-controls {
  display: grid;
  grid-template-columns: 1fr auto 1fr;
  align-items: center;
  margin-bottom: 1.25rem;
  width: 100%;
  max-width: 900px;
}

.toggle-group {
  grid-column: 2;
}

.view-controls .refresh-btn {
  grid-column: 3;
  justify-self: end;
  margin-left: 1.5rem;
}

.toggle-group {
  display: flex;
  border: 1px solid #252b50;
  border-radius: 999px;
  overflow: hidden;
}

.toggle-btn {
  padding: 0.5rem 1.25rem;
  background: transparent;
  color: #8090b4;
  border: none;
  font-family: 'DM Mono', monospace;
  font-size: 0.76rem;
  cursor: pointer;
  letter-spacing: 0.06em;
  transition: background 0.2s, color 0.2s;
}

.toggle-btn.active {
  background: #60d4f7;
  color: #0a0c18;
  font-weight: 600;
}

.toggle-btn:not(.active):hover {
  color: #60d4f7;
  background: rgba(96, 212, 247, 0.07);
}

</style>