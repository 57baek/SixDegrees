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
  // more tests added in Step 1.4

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
  })
})
