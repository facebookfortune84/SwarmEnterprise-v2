import { Toaster, toast as hotToast } from 'react-hot-toast'

export { Toaster }

const DURATION_MS = 8_000

export const toast = {
  success: (message: string, duration = DURATION_MS) =>
    hotToast.success(message, {
      duration,
      style: {
        background: '#052e16',
        color: '#86efac',
        border: '1px solid #166534',
      },
    }),

  error: (message: string, duration = DURATION_MS) =>
    hotToast.error(message, {
      duration,
      style: {
        background: '#450a0a',
        color: '#fca5a5',
        border: '1px solid #991b1b',
      },
    }),

  info: (message: string, duration = DURATION_MS) =>
    hotToast(message, {
      duration,
      icon: 'ℹ️',
      style: {
        background: '#172554',
        color: '#93c5fd',
        border: '1px solid #1e3a8a',
      },
    }),

  warning: (message: string, duration = DURATION_MS) =>
    hotToast(message, {
      duration,
      icon: '⚠️',
      style: {
        background: '#451a03',
        color: '#fcd34d',
        border: '1px solid #78350f',
      },
    }),

  dismiss: hotToast.dismiss,
}
