import { describe, it, expect } from 'vitest'
import { render } from '@testing-library/react'
import { Toaster } from 'react-hot-toast'
import { toast } from '@/components/ui/Toast'

describe('Toast', () => {
  it('has toast.success, error, info, warning methods', () => {
    expect(typeof toast.success).toBe('function')
    expect(typeof toast.error).toBe('function')
    expect(typeof toast.info).toBe('function')
    expect(typeof toast.warning).toBe('function')
  })

  it('has dismiss method', () => {
    expect(typeof toast.dismiss).toBe('function')
  })

  it('Toaster component renders without errors', () => {
    const { unmount } = render(<Toaster />)
    unmount()
  })
})
