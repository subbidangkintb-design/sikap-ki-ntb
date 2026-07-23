import { useEffect, useRef, useState } from 'react'
import { Mic, MicOff } from 'lucide-react'

const speechErrors = {
  'not-allowed': 'Izin mikrofon ditolak. Izinkan akses mikrofon pada pengaturan situs browser.',
  'service-not-allowed': 'Layanan pengenal suara tidak diizinkan oleh browser.',
  'audio-capture': 'Mikrofon tidak ditemukan atau sedang digunakan aplikasi lain.',
  network: 'Pengenalan suara gagal terhubung. Periksa koneksi internet.',
  'no-speech': 'Belum ada suara yang terdeteksi. Tekan mikrofon lalu bicara kembali.',
}

export default function SpeechToTextButton({ value, onChange, disabled = false }) {
  const recognitionRef = useRef(null)
  const [isListening, setIsListening] = useState(false)
  const [error, setError] = useState('')
  const SpeechRecognition = typeof window !== 'undefined'
    ? window.SpeechRecognition || window.webkitSpeechRecognition
    : null

  useEffect(() => () => recognitionRef.current?.abort(), [])

  function stopListening() {
    recognitionRef.current?.stop()
  }

  function startListening() {
    if (!SpeechRecognition) {
      setError('Browser ini belum mendukung speech-to-text. Gunakan Google Chrome atau Microsoft Edge terbaru.')
      return
    }

    setError('')
    const recognition = new SpeechRecognition()
    const initialText = value.trim()
    recognition.lang = 'id-ID'
    recognition.continuous = false
    recognition.interimResults = true
    recognition.maxAlternatives = 1

    recognition.onstart = () => setIsListening(true)
    recognition.onresult = (event) => {
      const spokenText = Array.from(event.results)
        .map((result) => result[0]?.transcript || '')
        .join(' ')
        .trim()
      onChange([initialText, spokenText].filter(Boolean).join(initialText ? ' ' : ''))
    }
    recognition.onerror = (event) => {
      if (event.error !== 'aborted') {
        setError(speechErrors[event.error] || 'Ucapan belum berhasil dikenali. Silakan coba kembali.')
      }
    }
    recognition.onend = () => {
      setIsListening(false)
      recognitionRef.current = null
    }
    recognitionRef.current = recognition

    try {
      recognition.start()
    } catch {
      setError('Mikrofon belum dapat dimulai. Tunggu sebentar lalu coba kembali.')
      setIsListening(false)
    }
  }

  return (
    <div className="flex flex-col items-start gap-1">
      <button
        type="button"
        onClick={isListening ? stopListening : startListening}
        disabled={disabled}
        aria-pressed={isListening}
        aria-label={isListening ? 'Hentikan perekaman suara' : 'Mulai mengetik dengan suara Bahasa Indonesia'}
        className={`inline-flex min-h-14 items-center justify-center gap-2 rounded-lg border px-4 font-bold transition disabled:cursor-not-allowed disabled:opacity-50 ${
          isListening
            ? 'animate-pulse border-red-300 bg-red-50 text-red-700'
            : 'border-gov-line bg-white text-gov-navy hover:border-gov-teal hover:bg-teal-50'
        }`}
      >
        {isListening ? <MicOff size={20} aria-hidden="true" /> : <Mic size={20} aria-hidden="true" />}
        <span className="md:sr-only">{isListening ? 'Selesai' : 'Bicara'}</span>
      </button>
      {isListening ? <span className="text-xs font-semibold text-red-700" role="status">Mendengarkan Bahasa Indonesia…</span> : null}
      {error ? <span className="max-w-xs text-xs leading-5 text-red-700" role="alert">{error}</span> : null}
    </div>
  )
}
