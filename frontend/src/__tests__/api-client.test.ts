/**
 * Tests for the API client module.
 */

import { describe, it, expect, beforeEach, vi } from 'vitest'

// Mock localStorage
const storage: Record<string, string> = {}
const localStorageMock = {
  getItem: vi.fn((key: string) => storage[key] ?? null),
  setItem: vi.fn((key: string, value: string) => { storage[key] = value }),
  removeItem: vi.fn((key: string) => { delete storage[key] }),
  clear: vi.fn(() => Object.keys(storage).forEach(k => delete storage[k])),
  length: 0,
  key: vi.fn(),
}
Object.defineProperty(globalThis, 'localStorage', { value: localStorageMock })

describe('API Client', () => {
  beforeEach(() => {
    localStorageMock.clear()
    vi.clearAllMocks()
  })

  it('getToken returns null when no token is stored', () => {
    const { getToken } = require('@/api/auth') as typeof import('@/api/auth')
    expect(getToken()).toBeNull()
  })

  it('getToken returns the stored token', () => {
    storage['quantitext-token'] = 'test-jwt-token'
    const { getToken } = require('@/api/auth') as typeof import('@/api/auth')
    expect(getToken()).toBe('test-jwt-token')
  })

  it('logout removes the token and redirects', () => {
    storage['quantitext-token'] = 'test-jwt-token'
    
    // Mock window.location
    const originalLocation = window.location
    Object.defineProperty(window, 'location', {
      writable: true,
      value: { href: '' },
    })

    const { logout } = require('@/api/auth') as typeof import('@/api/auth')
    logout()

    expect(localStorageMock.removeItem).toHaveBeenCalledWith('quantitext-token')
    expect(window.location.href).toBe('/login')

    // Restore
    Object.defineProperty(window, 'location', {
      writable: true,
      value: originalLocation,
    })
  })
})
