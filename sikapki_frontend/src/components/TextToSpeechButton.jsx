import { useEffect, useRef, useState } from 'react'
import { Pause, Play, RotateCcw, Square } from 'lucide-react'

export default function TextToSpeechButton({ text }) {
  const [state, setState] = useState('idle')
  const [rate, setRate] = useState('1')
  const utteranceRef = useRef(null)
  const supported = typeof window !== 'undefined' && 'speechSynthesis' in window

  useEffect(() => () => {
    if (utteranceRef.current) window.speechSynthesis.cancel()
  }, [])

  function speak() {
    if (!supported || !text?.trim()) return
    window.speechSynthesis.cancel()
    const utterance = new SpeechSynthesisUtterance(text)
    utterance.lang = 'id-ID'
    utterance.rate = Number(rate)
    utterance.onend = () => setState('idle')
    utterance.onerror = () => setState('idle')
    utteranceRef.current = utterance
    setState('speaking')
    window.speechSynthesis.speak(utterance)
  }

  function togglePause() {
    if (state === 'speaking') {
      window.speechSynthesis.pause()
      setState('paused')
    } else {
      window.speechSynthesis.resume()
      setState('speaking')
    }
  }

  function stop() {
    window.speechSynthesis.cancel()
    utteranceRef.current = null
    setState('idle')
  }

  if (!supported) return null

  return (
    <div className="mt-3 flex flex-wrap items-center gap-2 border-t border-gov-line pt-3" aria-label="Kontrol pembaca jawaban">
      {state === 'idle' ? (
        <button type="button" onClick={speak} className="inline-flex min-h-10 items-center gap-2 rounded-lg border border-gov-line bg-white px-3 text-xs font-bold text-gov-blue focus:outline-none focus:ring-4 focus:ring-gov-mint">
          <Play size={15} aria-hidden="true" /> Bacakan jawaban
        </button>
      ) : (
        <>
          <button type="button" onClick={togglePause} className="inline-flex min-h-10 items-center gap-2 rounded-lg border border-gov-line bg-white px-3 text-xs font-bold text-gov-blue focus:outline-none focus:ring-4 focus:ring-gov-mint">
            {state === 'paused' ? <RotateCcw size={15} aria-hidden="true" /> : <Pause size={15} aria-hidden="true" />}
            {state === 'paused' ? 'Lanjutkan' : 'Jeda'}
          </button>
          <button type="button" onClick={stop} className="inline-flex min-h-10 items-center gap-2 rounded-lg border border-gov-line bg-white px-3 text-xs font-bold text-red-700 focus:outline-none focus:ring-4 focus:ring-red-200">
            <Square size={14} aria-hidden="true" /> Berhenti
          </button>
        </>
      )}
      <label className="flex min-h-10 items-center gap-2 text-xs font-semibold text-slate-600">
        Kecepatan
        <select value={rate} onChange={(event) => { setRate(event.target.value); if (state !== 'idle') stop() }} className="h-10 rounded-lg border border-gov-line bg-white px-2 text-sm text-gov-navy">
          <option value="0.75">Lambat</option>
          <option value="1">Normal</option>
          <option value="1.25">Cepat</option>
        </select>
      </label>
      <span className="sr-only" aria-live="polite">{state === 'speaking' ? 'Jawaban sedang dibacakan' : state === 'paused' ? 'Pembacaan dijeda' : ''}</span>
    </div>
  )
}
