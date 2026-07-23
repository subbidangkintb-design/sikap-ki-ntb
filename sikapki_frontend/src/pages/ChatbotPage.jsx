import { useEffect, useRef, useState } from 'react'
import { AlertTriangle, Bot, Loader2, MessageCircle, RotateCcw, Send, ThumbsDown, ThumbsUp, UserRound } from 'lucide-react'
import { Link } from 'react-router-dom'
import PageHeader from '../components/PageHeader.jsx'
import StatusNotice from '../components/StatusNotice.jsx'
import SpeechToTextButton from '../components/SpeechToTextButton.jsx'
import FormattedResponse from '../components/FormattedResponse.jsx'
import TextToSpeechButton from '../components/TextToSpeechButton.jsx'
import { kirimRating, tanyaChatbot } from '../lib/api.js'
import { HELPDESK_WHATSAPP_URL } from '../config/service.js'

export default function ChatbotPage() {
  const [messages, setMessages] = useState(createInitialMessages)
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState('')
  const formRef = useRef(null)
  const sessionIdRef = useRef(createSessionId())
  const messageEndRef = useRef(null)

  useEffect(() => {
    messageEndRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' })
  }, [messages, isLoading])

  async function handleSubmit(event) {
    event.preventDefault()
    const question = input.trim()
    if (!question || isLoading) return

    setInput('')
    setError('')
    setMessages((current) => [...current, { id: createMessageId(), role: 'user', text: question }])
    setIsLoading(true)

    try {
      const response = await tanyaChatbot(question, sessionIdRef.current)
      if (response.sesi_id) sessionIdRef.current = response.sesi_id
      const sources = Array.isArray(response.sumber_dokumen)
        ? response.sumber_dokumen.filter((source) => source && typeof source.judul === 'string')
        : []
      setMessages((current) => [
        ...current,
        {
          id: response.id || createMessageId(),
          role: 'ai',
          text: typeof response.jawaban === 'string' ? response.jawaban : String(response.jawaban || ''),
          sources,
          escalated: Boolean(response.dieskalasi),
          rating: null,
          trackingId: response.pelacakan_id || null,
          consultationCode: response.kode_konsultasi || null,
        },
      ])
    } catch (err) {
      setError(err.message)
    } finally {
      setIsLoading(false)
    }
  }

  async function handleRating(messageId, value) {
    setMessages((current) => current.map((message) => (
      message.id === messageId ? { ...message, rating: value, ratingLoading: true } : message
    )))
    try {
      await kirimRating(messageId, value)
      setMessages((current) => current.map((message) => (
        message.id === messageId ? { ...message, rating: value, ratingLoading: false } : message
      )))
    } catch (err) {
      setMessages((current) => current.map((message) => (
        message.id === messageId ? { ...message, ratingLoading: false } : message
      )))
      setError(err.message)
    }
  }

  function handleNewConversation() {
    if (isLoading) return
    sessionIdRef.current = createSessionId()
    setMessages(createInitialMessages())
    setInput('')
    setError('')
  }

  return (
    <>
      <PageHeader
        eyebrow="Chatbot Helpdesk KI"
        title="Informasi awal berbasis pengetahuan resmi"
        description="Ajukan pertanyaan dengan bahasa sehari-hari. Sistem menampilkan sumber dokumen dan mengeskalasi kebutuhan kompleks kepada petugas Helpdesk KI Kanwil."
      />
      <section className="mx-auto max-w-5xl px-4 py-8">
        {error ? (
          <div className="mb-4">
            <StatusNotice tone="error" title="Chatbot belum berhasil merespons">
              {error}
            </StatusNotice>
          </div>
        ) : null}

        <div className="rounded-lg border border-gov-line bg-white shadow-soft">
          <div className="flex flex-wrap items-center justify-between gap-3 border-b border-gov-line bg-gov-paper px-4 py-3 md:px-6">
            <p className="text-sm text-slate-600"><strong className="text-gov-navy">Percakapan aktif.</strong> Pertanyaan lanjutan akan memahami topik sebelumnya.</p>
            <button type="button" onClick={handleNewConversation} disabled={isLoading} className="inline-flex items-center gap-2 rounded-md border border-gov-line bg-white px-3 py-2 text-sm font-bold text-gov-blue hover:border-gov-teal disabled:opacity-50">
              <RotateCcw size={16} aria-hidden="true" /> Percakapan baru
            </button>
          </div>
          <div className="h-[52dvh] min-h-[320px] overflow-y-auto overscroll-contain p-3 sm:h-[58vh] sm:min-h-[420px] sm:p-4 md:p-6">
            <div className="space-y-5" role="log" aria-live="polite" aria-relevant="additions" aria-label="Percakapan chatbot">
              {messages.map((message) => (
                <ChatMessage key={message.id} message={message} onRating={handleRating} />
              ))}
              {isLoading ? (
                <div className="flex items-center gap-3 text-sm text-slate-600" role="status">
                  <Loader2 className="h-5 w-5 animate-spin text-gov-teal" aria-hidden="true" />
                  Sedang menelusuri sumber dan menyusun jawaban...
                </div>
              ) : null}
              <div ref={messageEndRef} />
            </div>
          </div>
          <form ref={formRef} onSubmit={handleSubmit} className="border-t border-gov-line bg-gov-paper p-4">
            <div className="flex flex-col gap-3 md:flex-row">
              <label htmlFor="chat-input" className="sr-only">Pertanyaan</label>
              <textarea
                id="chat-input"
                value={input}
                onChange={(event) => setInput(event.target.value)}
                className="min-h-20 flex-1 rounded-md border border-gov-line px-3 py-3 outline-none focus:border-gov-teal focus:ring-2 focus:ring-gov-mint"
                placeholder="Contoh: Apa saja syarat daftar merek?"
                aria-describedby="chat-input-help"
              />
              <SpeechToTextButton value={input} onChange={setInput} disabled={isLoading} />
              <button
                type="submit"
                disabled={isLoading || !input.trim()}
                className="inline-flex min-h-14 items-center justify-center gap-2 rounded-lg bg-gov-teal px-6 font-bold text-white hover:bg-teal-700 disabled:cursor-not-allowed disabled:bg-slate-400"
              >
                <Send size={20} aria-hidden="true" />
                Kirim
              </button>
            </div>
            <p id="chat-input-help" className="mt-2 text-xs leading-5 text-slate-500">Tekan <strong>Bicara</strong>, izinkan mikrofon, lalu ucapkan pertanyaan dalam Bahasa Indonesia. Audio ditangani layanan pengenal suara browser dan tidak disimpan oleh portal SIKAP-KI.</p>
          </form>
        </div>
      </section>
    </>
  )
}

function createMessageId() {
  if (typeof globalThis.crypto?.randomUUID === 'function') {
    return globalThis.crypto.randomUUID()
  }
  return `message-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`
}

function createInitialMessages() {
  return [{
    id: 'welcome',
    role: 'ai',
    text: 'Selamat datang di layanan informasi SIKAP-KI NTB. Silakan ajukan pertanyaan tentang Kekayaan Intelektual. Anda dapat melanjutkan dengan pertanyaan seperti "apa syaratnya?", "berapa biayanya?", atau "setelah itu bagaimana?".',
    sources: [],
    escalated: false,
  }]
}

function createSessionId() {
  if (typeof globalThis.crypto?.randomUUID === 'function') return globalThis.crypto.randomUUID()
  return `00000000-0000-4000-8000-${Date.now().toString().padStart(12, '0').slice(-12)}`
}

function ChatMessage({ message, onRating }) {
  if (message.role === 'user') {
    return (
      <div className="flex justify-end">
        <div className="max-w-[92%] rounded-lg bg-gov-blue px-3 py-3 text-white sm:max-w-[82%] sm:px-4">
          <div className="mb-1 flex items-center justify-end gap-2 text-xs font-bold text-blue-100">
            Anda <UserRound size={15} aria-hidden="true" />
          </div>
          <p className="whitespace-pre-line text-sm leading-6">{message.text}</p>
        </div>
      </div>
    )
  }

  if (message.escalated) {
    return (
      <div className="max-w-3xl rounded-lg border border-amber-200 bg-amber-50 p-4 text-amber-950">
        <div className="mb-2 flex items-center gap-2 font-bold">
          <AlertTriangle size={19} aria-hidden="true" />
          Perlu arahan petugas
        </div>
        <FormattedResponse text={message.text} className="text-sm text-amber-950" />
        <TextToSpeechButton text={message.text} />
        <a href={HELPDESK_WHATSAPP_URL} target="_blank" rel="noreferrer" className="mt-4 inline-flex items-center gap-2 rounded-lg bg-[#128c4a] px-4 py-2 text-sm font-bold text-white">
          <MessageCircle size={17} /> Hubungi Helpdesk KI Kanwil
        </a>
        {message.trackingId ? (
          <div className="mt-3 rounded-lg border border-amber-300 bg-white p-3 text-sm">
            <p className="font-black">Nomor konsultasi: {message.consultationCode}</p>
            <Link to={`/status-konsultasi/${message.trackingId}`} className="mt-2 inline-flex font-bold text-gov-blue hover:underline">Pantau tindak lanjut petugas →</Link>
          </div>
        ) : null}
        <RatingControls message={message} onRating={onRating} />
      </div>
    )
  }

  return (
    <div className="flex justify-start">
      <div className="max-w-[94%] rounded-lg border border-gov-line bg-white px-3 py-3 shadow-sm sm:max-w-[86%] sm:px-4">
        <div className="mb-2 flex items-center gap-2 text-xs font-bold text-gov-teal">
          <Bot size={16} aria-hidden="true" />
          SIKAP-KI NTB
        </div>
        <FormattedResponse text={message.text} className="text-sm text-slate-800" />
        <TextToSpeechButton text={message.text} />
        {message.sources?.length ? (
          <div className="mt-3 rounded-md bg-gov-paper p-3">
            <p className="text-xs font-bold uppercase tracking-wide text-gov-navy">Sumber dokumen</p>
            <div className="mt-2 flex flex-wrap gap-2">
              {message.sources.map((source) => (
                source.url ? (
                  <a key={`${source.judul}-${source.url}`} href={source.url} target="_blank" rel="noreferrer" className="rounded-md border border-gov-line bg-white px-2 py-1 text-xs font-bold text-gov-blue hover:underline">
                    {source.judul} ↗
                  </a>
                ) : (
                  <span key={source.judul} className="rounded-md border border-gov-line bg-white px-2 py-1 text-xs text-slate-700">{source.judul}</span>
                )
              ))}
            </div>
          </div>
        ) : null}
        <RatingControls message={message} onRating={onRating} />
      </div>
    </div>
  )
}

function RatingControls({ message, onRating }) {
  if (message.id === 'welcome') return null
  return (
    <div className="mt-3 flex flex-wrap items-center gap-2 border-t border-gov-line pt-3">
      <span className="text-xs font-semibold text-slate-600">Apakah jawaban ini membantu?</span>
      <button
        type="button"
        onClick={() => onRating(message.id, true)}
        disabled={message.ratingLoading}
        className={`inline-flex items-center gap-1 rounded-md border px-2 py-1 text-xs font-bold ${
          message.rating === true ? 'border-emerald-400 bg-emerald-50 text-emerald-800' : 'border-gov-line bg-white text-slate-700'
        }`}
      >
        <ThumbsUp size={14} aria-hidden="true" />
        Ya
      </button>
      <button
        type="button"
        onClick={() => onRating(message.id, false)}
        disabled={message.ratingLoading}
        className={`inline-flex items-center gap-1 rounded-md border px-2 py-1 text-xs font-bold ${
          message.rating === false ? 'border-red-300 bg-red-50 text-red-800' : 'border-gov-line bg-white text-slate-700'
        }`}
      >
        <ThumbsDown size={14} aria-hidden="true" />
        Tidak
      </button>
    </div>
  )
}
