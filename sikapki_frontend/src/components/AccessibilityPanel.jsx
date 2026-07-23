import { useEffect, useId, useRef, useState } from 'react'
import { Accessibility, Check, RotateCcw, X } from 'lucide-react'

const STORAGE_KEY = 'sikapki-accessibility-preferences'
const defaults = { textSize: 'normal', highContrast: false, reduceMotion: false }

function loadPreferences() {
  try {
    return { ...defaults, ...JSON.parse(localStorage.getItem(STORAGE_KEY) || '{}') }
  } catch {
    return defaults
  }
}

export default function AccessibilityPanel() {
  const [open, setOpen] = useState(false)
  const [preferences, setPreferences] = useState(loadPreferences)
  const closeButtonRef = useRef(null)
  const triggerRef = useRef(null)
  const panelRef = useRef(null)

  useEffect(() => {
    const root = document.documentElement
    root.dataset.textSize = preferences.textSize
    root.dataset.highContrast = String(preferences.highContrast)
    root.dataset.reduceMotion = String(preferences.reduceMotion)
    localStorage.setItem(STORAGE_KEY, JSON.stringify(preferences))
  }, [preferences])

  useEffect(() => {
    if (!open) return undefined
    closeButtonRef.current?.focus()
    const handlePanelKeys = (event) => {
      if (event.key === 'Escape') {
        setOpen(false)
        triggerRef.current?.focus()
        return
      }
      if (event.key === 'Tab') {
        const focusable = panelRef.current?.querySelectorAll('button, input, select, textarea, a[href]')
        if (!focusable?.length) return
        const first = focusable[0]
        const last = focusable[focusable.length - 1]
        if (event.shiftKey && document.activeElement === first) {
          event.preventDefault()
          last.focus()
        } else if (!event.shiftKey && document.activeElement === last) {
          event.preventDefault()
          first.focus()
        }
      }
    }
    window.addEventListener('keydown', handlePanelKeys)
    return () => window.removeEventListener('keydown', handlePanelKeys)
  }, [open])

  function update(key, value) {
    setPreferences((current) => ({ ...current, [key]: value }))
  }

  return (
    <>
      <button
        ref={triggerRef}
        type="button"
        onClick={() => setOpen(true)}
        className="fixed bottom-[max(0.75rem,env(safe-area-inset-bottom))] left-3 z-50 inline-flex min-h-12 items-center gap-2 rounded-full border-2 border-gov-navy bg-white px-3 font-black text-gov-navy shadow-lg focus:outline-none focus:ring-4 focus:ring-gov-gold sm:bottom-5 sm:left-5"
        aria-haspopup="dialog"
        aria-expanded={open}
      >
        <Accessibility size={22} aria-hidden="true" />
        <span className="hidden sm:inline">Aksesibilitas</span>
      </button>

      {open ? (
        <div className="fixed inset-0 z-[60] flex items-end bg-slate-950/50 p-3 sm:items-center sm:justify-center">
          <section ref={panelRef} role="dialog" aria-modal="true" aria-labelledby="accessibility-title" className="w-full rounded-2xl bg-white p-5 text-gov-navy shadow-2xl sm:max-w-md">
            <div className="flex items-center justify-between gap-4">
              <h2 id="accessibility-title" className="text-xl font-black">Pengaturan aksesibilitas</h2>
              <button ref={closeButtonRef} type="button" onClick={() => { setOpen(false); triggerRef.current?.focus() }} className="inline-flex h-11 w-11 items-center justify-center rounded-xl border border-gov-line focus:outline-none focus:ring-4 focus:ring-gov-mint" aria-label="Tutup pengaturan aksesibilitas">
                <X size={22} aria-hidden="true" />
              </button>
            </div>

            <fieldset className="mt-5">
              <legend className="font-black">Ukuran teks</legend>
              <div className="mt-2 grid grid-cols-3 gap-2">
                {[['normal', 'Normal'], ['large', 'Besar'], ['xlarge', 'Sangat besar']].map(([value, label]) => (
                  <button key={value} type="button" aria-pressed={preferences.textSize === value} onClick={() => update('textSize', value)} className={`min-h-12 rounded-xl border px-2 text-sm font-bold ${preferences.textSize === value ? 'border-gov-blue bg-blue-50 ring-2 ring-gov-mint' : 'border-gov-line'}`}>
                    {preferences.textSize === value ? <Check className="mr-1 inline" size={16} aria-hidden="true" /> : null}{label}
                  </button>
                ))}
              </div>
            </fieldset>

            <div className="mt-5 space-y-3">
              <PreferenceToggle label="Kontras tinggi" description="Mempertegas teks, garis, dan kontrol." checked={preferences.highContrast} onChange={(value) => update('highContrast', value)} />
              <PreferenceToggle label="Kurangi animasi" description="Mengurangi gerakan dan transisi antarmuka." checked={preferences.reduceMotion} onChange={(value) => update('reduceMotion', value)} />
            </div>

            <button type="button" onClick={() => setPreferences(defaults)} className="mt-5 inline-flex min-h-11 w-full items-center justify-center gap-2 rounded-xl border border-gov-line font-bold focus:outline-none focus:ring-4 focus:ring-gov-mint">
              <RotateCcw size={18} aria-hidden="true" /> Kembalikan pengaturan awal
            </button>
          </section>
        </div>
      ) : null}
    </>
  )
}

function PreferenceToggle({ label, description, checked, onChange }) {
  const id = useId()
  return (
    <div className="flex items-center justify-between gap-4 rounded-xl border border-gov-line p-3">
      <span><label htmlFor={id} className="block cursor-pointer font-black">{label}</label><span className="mt-1 block text-xs text-slate-600">{description}</span></span>
      <input id={id} type="checkbox" checked={checked} onChange={(event) => onChange(event.target.checked)} className="h-6 w-6 shrink-0 accent-gov-blue" />
    </div>
  )
}
