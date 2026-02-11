import { useEffect, useMemo, useState } from 'react'

export type TutorialStep = {
  selector: string
  title: string
  description: string
  details?: string[]
}

type GuidedTutorialProps = {
  steps: TutorialStep[]
  startLabel?: string
  onStart?: () => void
  buttonClassName?: string
}

const clamp = (value: number, min: number, max: number) => Math.min(max, Math.max(min, value))

export function GuidedTutorial({
  steps,
  startLabel = 'Tutorial',
  onStart,
  buttonClassName = 'ghost',
}: GuidedTutorialProps) {
  const [open, setOpen] = useState(false)
  const [stepIndex, setStepIndex] = useState(0)
  const [targetRect, setTargetRect] = useState<DOMRect | null>(null)
  const [targetFound, setTargetFound] = useState(true)

  const hasSteps = steps.length > 0
  const current = hasSteps ? steps[stepIndex] : null

  useEffect(() => {
    if (!open || !current) return

    const update = () => {
      const node = document.querySelector(current.selector) as HTMLElement | null
      if (!node) {
        setTargetFound(false)
        setTargetRect(null)
        return
      }

      setTargetFound(true)
      node.scrollIntoView({ block: 'center', inline: 'nearest', behavior: 'smooth' })
      setTargetRect(node.getBoundingClientRect())
    }

    const timer = window.setTimeout(update, 120)
    window.addEventListener('resize', update)
    window.addEventListener('scroll', update, true)

    return () => {
      window.clearTimeout(timer)
      window.removeEventListener('resize', update)
      window.removeEventListener('scroll', update, true)
    }
  }, [open, current, stepIndex])

  const cardStyle = useMemo(() => {
    const fallback = { top: 24, left: 24 }
    if (!open || typeof window === 'undefined') return fallback
    if (!targetRect) return fallback

    const cardWidth = Math.min(420, window.innerWidth - 32)
    const margin = 16
    const preferredTop = targetRect.bottom + 12
    const preferredLeft = targetRect.left
    const maxLeft = Math.max(margin, window.innerWidth - cardWidth - margin)

    let top = preferredTop
    if (preferredTop > window.innerHeight - 240) {
      top = Math.max(margin, targetRect.top - 220)
    }

    return {
      top: clamp(top, margin, Math.max(margin, window.innerHeight - 220)),
      left: clamp(preferredLeft, margin, maxLeft),
    }
  }, [open, targetRect])

  const startTutorial = () => {
    if (!hasSteps) return
    onStart?.()
    setStepIndex(0)
    setOpen(true)
  }

  const closeTutorial = () => {
    setOpen(false)
    setTargetRect(null)
    setTargetFound(true)
  }

  const nextStep = () => {
    if (!hasSteps) return
    if (stepIndex >= steps.length - 1) {
      closeTutorial()
      return
    }
    setStepIndex((prev) => prev + 1)
  }

  const prevStep = () => {
    setStepIndex((prev) => Math.max(0, prev - 1))
  }

  return (
    <>
      <button type="button" className={buttonClassName} onClick={startTutorial} data-testid="tutorial-start-btn">
        {startLabel}
      </button>

      {open && current && (
        <div
          aria-live="polite"
          role="dialog"
          aria-label="Interactive tutorial"
          style={{
            position: 'fixed',
            inset: 0,
            zIndex: 2147483000,
            pointerEvents: 'none',
          }}
        >
          {targetRect && (
            <div
              style={{
                position: 'fixed',
                top: Math.max(6, targetRect.top - 6),
                left: Math.max(6, targetRect.left - 6),
                width: Math.max(0, targetRect.width + 12),
                height: Math.max(0, targetRect.height + 12),
                borderRadius: 12,
                border: '3px solid #1f5bff',
                boxShadow: '0 0 0 9999px rgba(10, 12, 22, 0.56)',
                pointerEvents: 'none',
              }}
            />
          )}

          <div
            style={{
              position: 'fixed',
              top: cardStyle.top,
              left: cardStyle.left,
              width: 'min(420px, calc(100vw - 32px))',
              background: '#ffffff',
              border: '2px solid #111113',
              borderRadius: 12,
              boxShadow: '8px 8px 0 rgba(17,17,19,0.92)',
              padding: 14,
              color: '#111113',
              pointerEvents: 'auto',
              fontFamily: 'Space Grotesk, Segoe UI, sans-serif',
            }}
          >
            <div
              style={{
                fontFamily: 'Space Mono, ui-monospace, SFMono-Regular, Menlo, monospace',
                letterSpacing: '0.08em',
                textTransform: 'uppercase',
                fontSize: 12,
                color: '#475569',
                marginBottom: 6,
              }}
            >
              Step {stepIndex + 1} / {steps.length}
            </div>
            <div style={{ fontWeight: 700, fontSize: 17, marginBottom: 6 }}>{current.title}</div>
            <p style={{ margin: 0, lineHeight: 1.4 }}>{current.description}</p>
            {current.details && current.details.length > 0 && (
              <ul
                style={{
                  margin: '8px 0 0 16px',
                  padding: 0,
                  lineHeight: 1.35,
                  fontSize: 13,
                }}
              >
                {current.details.map((detail) => (
                  <li key={detail}>{detail}</li>
                ))}
              </ul>
            )}
            {!targetFound && (
              <p style={{ marginTop: 8, color: '#b45309', fontSize: 13 }}>
                This area is currently hidden. Continue and return to it when visible.
              </p>
            )}

            <div style={{ display: 'flex', gap: 8, marginTop: 12, flexWrap: 'wrap' }}>
              <button
                type="button"
                onClick={prevStep}
                disabled={stepIndex === 0}
                style={{
                  border: '2px solid #111113',
                  borderRadius: 8,
                  background: '#f8fafc',
                  padding: '6px 10px',
                  fontWeight: 600,
                  cursor: stepIndex === 0 ? 'not-allowed' : 'pointer',
                }}
              >
                Back
              </button>
              <button
                type="button"
                onClick={nextStep}
                style={{
                  border: '2px solid #111113',
                  borderRadius: 8,
                  background: '#1f5bff',
                  color: '#fff',
                  padding: '6px 10px',
                  fontWeight: 700,
                  cursor: 'pointer',
                }}
              >
                {stepIndex === steps.length - 1 ? 'Finish' : 'Next'}
              </button>
              <button
                type="button"
                onClick={closeTutorial}
                style={{
                  border: '2px solid #111113',
                  borderRadius: 8,
                  background: '#fff',
                  padding: '6px 10px',
                  fontWeight: 600,
                  cursor: 'pointer',
                }}
              >
                Skip
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  )
}
