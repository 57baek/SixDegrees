// src/tests/signup.test.js

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'

// ─── 1. Hoist mocks ───────────────────────────────────────────────────────────
const { push, signUp, rpc, alertMock } = vi.hoisted(() => ({
  push: vi.fn(),
  signUp: vi.fn(),
  rpc: vi.fn(),
  alertMock: vi.fn(),
}))

// ─── 2. Mock vue-router ───────────────────────────────────────────────────────
vi.mock('vue-router', () => ({
  useRouter: () => ({ push }),
}))

// ─── 3. Mock Supabase ─────────────────────────────────────────────────────────
vi.mock('../lib/supabase', () => ({
  supabase: {
    auth: { signUp },
    rpc,
  },
}))

import SignUp from '../views/SignUp.vue'

// ─── 4. Mount helper ──────────────────────────────────────────────────────────
const mountView = () =>
  mount(SignUp, {
    global: { stubs: { RouterLink: true } },
  })

// ─── 5. Helper: fill and submit the form ─────────────────────────────────────
const fillAndSubmit = async (wrapper, { nick = 'myNick', email = 'me@example.com', password = 'Valid123!' } = {}) => {
  const inputs = wrapper.findAll('input')
  await inputs[0].setValue(nick)
  await inputs[1].setValue(email)
  await inputs[2].setValue(password)
  await wrapper.find('form').trigger('submit.prevent')
  await flushPromises()
}

// ─────────────────────────────────────────────────────────────────────────────

describe('SignUp view', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.spyOn(console, 'error').mockImplementation(() => {})
    // Return a proper object so destructuring never fails
    signUp.mockResolvedValue({ data: {}, error: null })
    rpc.mockResolvedValue({ data: true, error: null })
    window.alert = alertMock
  })

  // ── SECTION: Rendering ────────────────────────────────────────────────────

  describe('Rendering', () => {
    it('renders the title and all form fields', () => {
      const wrapper = mountView()
      expect(wrapper.text()).toContain('Create a SixDegrees Account')
      expect(wrapper.text()).toContain('Nickname')
      expect(wrapper.text()).toContain('Email')
      expect(wrapper.text()).toContain('Password')
    })

    it('renders the Sign Up and back to login buttons', () => {
      const wrapper = mountView()
      expect(wrapper.find('button.signup-btn').exists()).toBe(true)
      expect(wrapper.find('button.back2login-btn').exists()).toBe(true)
    })
  })

  // ── SECTION: Validation UI ────────────────────────────────────────────────

  describe('Validation UI', () => {
    it('shows the nickname validation message when nickname input is focused', async () => {
      const wrapper = mountView()
      await wrapper.findAll('input')[0].trigger('focus')
      expect(wrapper.text()).toContain('Enter a valid nickname')
    })

    it('shows the password checklist when password input is focused', async () => {
      const wrapper = mountView()
      await wrapper.findAll('input')[2].trigger('focus')
      expect(wrapper.text()).toContain('At least 8 characters')
      expect(wrapper.text()).toContain('At least 1 uppercase letter')
      expect(wrapper.text()).toContain('At least 1 lowercase letter')
      expect(wrapper.text()).toContain('At least 1 number')
      expect(wrapper.text()).toContain('At least 1 special character')
    })

    it('hides the password checklist when password input loses focus', async () => {
      const wrapper = mountView()
      const passwordInput = wrapper.findAll('input')[2]
      await passwordInput.trigger('focus')
      await passwordInput.trigger('blur')
      expect(wrapper.text()).not.toContain('At least 8 characters')
    })
  })

  // ── SECTION: Nickname availability ───────────────────────────────────────

  describe('Nickname availability', () => {
    it('calls nickname_available RPC when nickname is typed', async () => {
      const wrapper = mountView()
      const nicknameInput = wrapper.findAll('input')[0]
      await nicknameInput.setValue('myNick')
      await nicknameInput.trigger('input')
      await flushPromises()
      expect(rpc).toHaveBeenCalledWith('nickname_available', { nickname: 'myNick' })
    })

    it('shows "Nickname is available" when RPC returns true', async () => {
      rpc.mockResolvedValue({ data: true, error: null })
      const wrapper = mountView()
      const nicknameInput = wrapper.findAll('input')[0]
      await nicknameInput.setValue('myNick')
      await nicknameInput.trigger('focus')
      await nicknameInput.trigger('input')
      await flushPromises()
      expect(wrapper.text()).toContain('Nickname is available')
    })

    it('shows "Nickname is not available" when RPC returns false', async () => {
      rpc.mockResolvedValue({ data: false, error: null })
      const wrapper = mountView()
      const nicknameInput = wrapper.findAll('input')[0]
      await nicknameInput.setValue('takenNick')
      await nicknameInput.trigger('focus')
      await nicknameInput.trigger('input')
      await flushPromises()
      expect(wrapper.text()).toContain('Nickname is not available')
    })
  })

  // ── SECTION: Form Submission ──────────────────────────────────────────────

  describe('Form Submission', () => {
    it('blocks submission and shows error when password is too weak', async () => {
      const wrapper = mountView()
      await fillAndSubmit(wrapper, { password: 'weak' })
      expect(signUp).not.toHaveBeenCalled()
      expect(wrapper.text()).toContain('Password does not meet the requirements.')
    })

    it('calls supabase.auth.signUp with correct data on valid submission', async () => {
      const wrapper = mountView()
      await fillAndSubmit(wrapper)
      expect(signUp).toHaveBeenCalledWith({
        email: 'me@example.com',
        password: 'Valid123!',
        options: { data: { nickname: 'myNick' } },
      })
    })

    it('alerts and redirects to /profile-setup on success', async () => {
      const wrapper = mountView()
      await fillAndSubmit(wrapper)
      expect(alertMock).toHaveBeenCalledWith(
        'Signup successful! You can now set up your profile.'
      )
      expect(push).toHaveBeenCalledWith('/profile-setup')
    })

    it('shows supabase error and does not redirect on failure', async () => {
      signUp.mockResolvedValue({ data: null, error: { message: 'Email already exists' } })
      const wrapper = mountView()
      await fillAndSubmit(wrapper)
      expect(wrapper.text()).toContain('Email already exists')
      expect(push).not.toHaveBeenCalled()
      expect(alertMock).not.toHaveBeenCalled()
    })
  })

  // ── SECTION: Navigation ───────────────────────────────────────────────────

  describe('Navigation', () => {
    it('navigates to /login when "I have an account" is clicked', async () => {
      const wrapper = mountView()
      await wrapper.find('button.back2login-btn').trigger('click')
      expect(push).toHaveBeenCalledWith('/login')
    })
  })
})