/**
 * Unit tests for LoginPage component including theme switcher.
 */

import { describe, it, expect, beforeEach } from 'vitest'
import { act } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import { ThemeProvider } from '@/store/theme-context'
import { LoginPage } from '@/pages/login'

// @ts-expect-error React act testing flag
globalThis.IS_REACT_ACT_ENVIRONMENT = true

describe('LoginPage', () => {
  let container: HTMLDivElement

  beforeEach(() => {
    localStorage.clear()
    document.documentElement.className = ''
    container = document.createElement('div')
    document.body.appendChild(container)
  })

  it('renders login form and credentials hint', () => {
    const root = createRoot(container)
    act(() => {
      root.render(
        <BrowserRouter>
          <ThemeProvider>
            <LoginPage />
          </ThemeProvider>
        </BrowserRouter>,
      )
    })

    expect(container.textContent).toContain('QuantiText')
    expect(container.textContent).toContain('AI-powered Business Intelligence')
    expect(container.textContent).toContain('Demo credentials')

    const emailInput = container.querySelector('#email') as HTMLInputElement
    const passwordInput = container.querySelector('#password') as HTMLInputElement
    const submitBtn = container.querySelector('#login-submit') as HTMLButtonElement

    expect(emailInput).not.toBeNull()
    expect(emailInput.value).toBe('admin@demo.local')
    expect(passwordInput).not.toBeNull()
    expect(passwordInput.value).toBe('admin123')
    expect(submitBtn).not.toBeNull()
  })

  it('renders theme toggle and toggles between light and dark mode', () => {
    const root = createRoot(container)
    act(() => {
      root.render(
        <BrowserRouter>
          <ThemeProvider>
            <LoginPage />
          </ThemeProvider>
        </BrowserRouter>,
      )
    })

    const themeToggle = container.querySelector('#login-theme-toggle') as HTMLButtonElement
    expect(themeToggle).not.toBeNull()

    const initialTheme = document.documentElement.classList.contains('dark') ? 'dark' : 'light'

    // Click theme toggle
    act(() => {
      themeToggle.click()
    })

    const newTheme = document.documentElement.classList.contains('dark') ? 'dark' : 'light'
    expect(newTheme).not.toBe(initialTheme)

    // Click again to toggle back
    act(() => {
      themeToggle.click()
    })

    const revertedTheme = document.documentElement.classList.contains('dark') ? 'dark' : 'light'
    expect(revertedTheme).toBe(initialTheme)
  })

  it('renders individual About and Contact Us options and opens separate modals with close buttons', () => {
    const root = createRoot(container)
    act(() => {
      root.render(
        <BrowserRouter>
          <ThemeProvider>
            <LoginPage />
          </ThemeProvider>
        </BrowserRouter>,
      )
    })

    const aboutBtn = container.querySelector('#login-about-btn') as HTMLButtonElement
    const contactBtn = container.querySelector('#login-contact-btn') as HTMLButtonElement

    expect(aboutBtn).not.toBeNull()
    expect(contactBtn).not.toBeNull()
    expect(aboutBtn.textContent).toContain('About')
    expect(contactBtn.textContent).toContain('Contact Us')

    // Click About button -> opens ONLY About modal
    act(() => {
      aboutBtn.click()
    })

    expect(document.body.textContent).toContain('About QuantiText')
    expect(document.body.textContent).toContain('Closed-Loop Decision Architecture')
    expect(document.body.textContent).not.toContain('Your Name') // Not contact form!

    const aboutCloseBtn = document.body.querySelector('#about-modal-close') as HTMLButtonElement
    expect(aboutCloseBtn).not.toBeNull()
    act(() => {
      aboutCloseBtn.click()
    })

    expect(document.body.textContent).not.toContain('About QuantiText')

    // Click Contact button -> opens ONLY Contact modal
    act(() => {
      contactBtn.click()
    })

    expect(document.body.textContent).toContain('Contact Us')
    expect(document.body.querySelector('#contact-name')).not.toBeNull()
    expect(document.body.querySelector('#contact-email')).not.toBeNull()
    expect(document.body.querySelector('#contact-message')).not.toBeNull()

    const contactCloseBtn = document.body.querySelector('#contact-modal-close') as HTMLButtonElement
    expect(contactCloseBtn).not.toBeNull()
    act(() => {
      contactCloseBtn.click()
    })

    expect(document.body.querySelector('#contact-name')).toBeNull()
  })
})
