import { describe, it, expect, vi, afterEach } from 'vitest'
import { mount } from '@vue/test-utils'

// vi.mock is hoisted by Vitest before imports — safe to place here
vi.mock('vue-router', () => ({
  useRouter: () => ({ push: vi.fn() }),
  useRoute: () => ({ params: {} }),
}))

vi.mock('../lib/supabase', () => ({
  supabase: {
    auth: {
      getUser: vi.fn().mockResolvedValue({ data: { user: { id: 'user-1' } } }),
      getSession: vi.fn().mockResolvedValue({ data: { session: { access_token: 'tok' } } }),
    },
  },
}))

import ClosenessMap from '../components/ClosenessMap.vue'

const MOCK_COORDS = [
  { user_id: 'you',   x: 0.0,  y: 0.0,  tier: 1, nickname: 'You',   display_name: 'You'   },
  { user_id: 'alice', x: 0.3,  y: 0.2,  tier: 1, nickname: 'Alice', display_name: 'Alice' },
  { user_id: 'bob',   x: -0.8, y: 0.6,  tier: 2, nickname: 'Bob',   display_name: 'Bob'   },
  { user_id: 'carol', x: 0.1,  y: -0.9, tier: 3, nickname: 'Carol', display_name: 'Carol' },
]

describe('ClosenessMap', () => {
  afterEach(() => vi.unstubAllGlobals())

  it('renders one node-group per non-YOU coordinate', () => {
    const wrapper = mount(ClosenessMap, {
      props: { rawCoordinates: MOCK_COORDS, svgW: 800, svgH: 560 },
    })
    expect(wrapper.findAll('.cl-node-group')).toHaveLength(3)
  })

  it('renders YOU text at the center node', () => {
    const wrapper = mount(ClosenessMap, {
      props: { rawCoordinates: MOCK_COORDS, svgW: 800, svgH: 560 },
    })
    expect(wrapper.text()).toContain('YOU')
  })

  it('renders a line for each non-YOU node', () => {
    const wrapper = mount(ClosenessMap, {
      props: { rawCoordinates: MOCK_COORDS, svgW: 800, svgH: 560 },
    })
    expect(wrapper.findAll('line')).toHaveLength(3)
  })

  it('handles empty rawCoordinates gracefully', () => {
    const wrapper = mount(ClosenessMap, {
      props: { rawCoordinates: [], svgW: 800, svgH: 560 },
    })
    expect(wrapper.findAll('.cl-node-group')).toHaveLength(0)
    expect(wrapper.text()).toContain('YOU')
  })

  it('handles all-zero coordinates without crashing (maxMagnitude guard)', () => {
    const allZero = [
      { user_id: 'you', x: 0, y: 0, tier: 1, display_name: 'You' },
      { user_id: 'a',   x: 0, y: 0, tier: 1, display_name: 'A'   },
    ]
    expect(() => mount(ClosenessMap, {
      props: { rawCoordinates: allZero, svgW: 800, svgH: 560 },
    })).not.toThrow()
    const wrapper = mount(ClosenessMap, {
      props: { rawCoordinates: allZero, svgW: 800, svgH: 560 },
    })
    expect(wrapper.findAll('.cl-node-group')).toHaveLength(0)
  })
})

import PeopleMap from '../views/PeopleMap.vue'

describe('PeopleMap toggle', () => {
  afterEach(() => vi.unstubAllGlobals())

  function mountWithFetch(responseOverride = {}) {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: vi.fn().mockResolvedValue({
        coordinates: [{ user_id: 'u1', x: 0.1, y: 0.2, tier: 1, display_name: 'Test' }],
        computed_at: new Date().toISOString(),
        ...responseOverride,
      }),
    }))
    return mount(PeopleMap)
  }

  async function flush() {
    await new Promise(r => setTimeout(r, 50))
  }

  it('shows Connections view by default (ClosenessMap not rendered)', async () => {
    const wrapper = mountWithFetch()
    await flush()
    expect(wrapper.findComponent(ClosenessMap).exists()).toBe(false)
  })

  it('shows ClosenessMap after clicking Closeness button', async () => {
    const wrapper = mountWithFetch()
    await flush()
    await wrapper.find('[data-view="closeness"]').trigger('click')
    expect(wrapper.findComponent(ClosenessMap).exists()).toBe(true)
  })

  it('hides ClosenessMap after switching back to Connections', async () => {
    const wrapper = mountWithFetch()
    await flush()
    await wrapper.find('[data-view="closeness"]').trigger('click')
    await wrapper.find('[data-view="connections"]').trigger('click')
    expect(wrapper.findComponent(ClosenessMap).exists()).toBe(false)
  })
})

describe('PeopleMap API wiring', () => {
  afterEach(() => vi.unstubAllGlobals())

  it('calls trigger endpoint when GET /map returns 404, and uses trigger response directly', async () => {
    const triggerPayload = {
      coordinates: [{ user_id: 'user-1', x: 0, y: 0, tier: 1, display_name: 'Me' }],
      computed_at: new Date().toISOString(),
    }
    const fetchMock = vi.fn()
      .mockResolvedValueOnce({ ok: false, status: 404, json: vi.fn() })
      .mockResolvedValueOnce({ ok: true, status: 200, json: vi.fn().mockResolvedValue(triggerPayload) })
    vi.stubGlobal('fetch', fetchMock)

    mount(PeopleMap)
    await new Promise(r => setTimeout(r, 100))

    // First call: GET /map/user-1
    expect(fetchMock.mock.calls[0][0]).toContain('/map/user-1')
    expect(fetchMock.mock.calls[0][1]?.method).toBeUndefined() // GET has no explicit method

    // Second call: POST /map/trigger/user-1
    expect(fetchMock.mock.calls[1][0]).toContain('/map/trigger/user-1')
    expect(fetchMock.mock.calls[1][1]?.method).toBe('POST')

    // Only 2 calls total — no redundant second GET
    expect(fetchMock).toHaveBeenCalledTimes(2)
  })
})
describe('PeopleMap loading state', () => {
  afterEach(() => vi.unstubAllGlobals())

  it('shows loading ring on mount before fetch resolves', () => {
    vi.stubGlobal('fetch', vi.fn(() => new Promise(() => {})))
    const wrapper = mount(PeopleMap)
    expect(wrapper.find('.loading-ring').exists()).toBe(true)
    expect(wrapper.text()).toContain('Loading')
  })

  it('hides loading ring after fetch completes', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: true, status: 200,
      json: vi.fn().mockResolvedValue({ coordinates: [], computed_at: new Date().toISOString() }),
    }))
    const wrapper = mount(PeopleMap)
    await new Promise(r => setTimeout(r, 50))
    expect(wrapper.find('.loading-ring').exists()).toBe(false)
  })
})

describe('PeopleMap rendering', () => {
  afterEach(() => vi.unstubAllGlobals())

  it('shows empty state when coordinates array is empty', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: true, status: 200,
      json: vi.fn().mockResolvedValue({ coordinates: [], computed_at: new Date().toISOString() }),
    }))
    const wrapper = mount(PeopleMap)
    await new Promise(r => setTimeout(r, 50))
    expect(wrapper.text()).toContain('No connections yet')
  })

  it('shows correct connection count in footer', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: true, status: 200,
      json: vi.fn().mockResolvedValue({
        coordinates: [
          { user_id: 'u1', x: 0.1, y: 0.2, tier: 1, display_name: 'Alice', nickname: 'Alice' },
          { user_id: 'u2', x: -0.3, y: 0.4, tier: 2, display_name: 'Bob', nickname: 'Bob' },
        ],
        computed_at: new Date().toISOString(),
      }),
    }))
    const wrapper = mount(PeopleMap)
    await new Promise(r => setTimeout(r, 50))
    expect(wrapper.text()).toContain('2 connections')
  })
})

describe('PeopleMap error state', () => {
  afterEach(() => vi.unstubAllGlobals())

  it('shows error message when fetch returns 500', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: false, status: 500,
      json: vi.fn().mockResolvedValue({}),
    }))
    const wrapper = mount(PeopleMap)
    await new Promise(r => setTimeout(r, 50))
    expect(wrapper.find('.state-box').exists()).toBe(true)
    expect(wrapper.text()).toContain("map hasn't been built yet")
  })
})

describe('PeopleMap mobile warning', () => {
  afterEach(() => vi.unstubAllGlobals())

  it('shows mobile warning when window width is under 600px', async () => {
    Object.defineProperty(window, 'innerWidth', { writable: true, configurable: true, value: 400 })
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: true, status: 200,
      json: vi.fn().mockResolvedValue({
        coordinates: [{ user_id: 'u1', x: 0.1, y: 0.2, tier: 1, display_name: 'Alice', nickname: 'Alice' }],
        computed_at: new Date().toISOString(),
      }),
    }))
    const wrapper = mount(PeopleMap)
    await new Promise(r => setTimeout(r, 50))
    expect(wrapper.find('.mobile-warn').exists()).toBe(true)
  })

  it('does not show mobile warning on desktop width', async () => {
    Object.defineProperty(window, 'innerWidth', { writable: true, configurable: true, value: 1280 })
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: true, status: 200,
      json: vi.fn().mockResolvedValue({
        coordinates: [{ user_id: 'u1', x: 0.1, y: 0.2, tier: 1, display_name: 'Alice', nickname: 'Alice' }],
        computed_at: new Date().toISOString(),
      }),
    }))
    const wrapper = mount(PeopleMap)
    await new Promise(r => setTimeout(r, 50))
    expect(wrapper.find('.mobile-warn').exists()).toBe(false)
  })
})
