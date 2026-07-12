import { useRef, useState } from 'react'
import { AlertTriangle, Bot, Loader2, Send, ThumbsDown, ThumbsUp, UserRound } from 'lucide-react'
import PageHeader from '../components/PageHeader.jsx'
import StatusNotice from '../components/StatusNotice.jsx'
import { kirimRating, tanyaChatbot } from '../lib/api.js'

export default function ChatbotPage() {
  const [messages, setMessages] = useState([
    {
      id: 'welcome',
      role: 'ai',
      text: 'Selamat datang. Silakan ajukan pertanyaan tentang layanan Kekayaan Intelektual. Saya akan menjawab berdasarkan konteks dokumen yang tersedia.',
      sources: [],
      escalated: false,
    },
  ])
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState('')
  const formRef = useRef(null)

  async function handleSubmit(event) {
    event.preventDefault()
    const question = input.trim()
    if (!question || isLoading) return

    setInput('')
    setError('')
    setMessages((current) => [...current, { id: crypto.randomUUID(), role: 'user', text: question }])
    setIsLoading(true)

    try {
      const response = await tanyaChatbot(question)
      setMessages((current) => [
        ...current,
        {
          id: response.id,
          role: 'ai',
          text: response.jawaban,
          sources: response.sumber_dokumen || [],
          escalated: response.dieskalasi,
          rating: null,
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

  return (
    <>
      <PageHeader
        eyebrow="Tanya AI"
        title="Chatbot informasi Kekayaan Intelektual"
        description="Ajukan pertanyaan dengan bahasa sehari-hari. Jawaban AI akan menampilkan sumber dokumen bila tersedia dan akan dieskalasi jika konteks tidak cukup."
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
          <div className="h-[58vh] min-h-[420px] overflow-y-auto p-4 md:p-6">
            <div className="space-y-5">
              {messages.map((message) => (
                <ChatMessage key={message.id} message={message} onRating={handleRating} />
              ))}
              {isLoading ? (
                <div className="flex items-center gap-3 text-sm text-slate-600">
                  <Loader2 className="h-5 w-5 animate-spin text-gov-teal" aria-hidden="true" />
                  AI sedang mencari konteks dan menyusun jawaban...
                </div>
              ) : null}
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
              />
              <button
                type="submit"
                disabled={isLoading || !input.trim()}
                className="inline-flex min-h-14 items-center justify-center gap-2 rounded-lg bg-gov-teal px-6 font-bold text-white hover:bg-teal-700 disabled:cursor-not-allowed disabled:bg-slate-400"
              >
                <Send size={20} aria-hidden="true" />
                Kirim
              </button>
            </div>
          </form>
        </div>
      </section>
    </>
  )
}

function ChatMessage({ message, onRating }) {
  if (message.role === 'user') {
    return (
      <div className="flex justify-end">
        <div className="max-w-[82%] rounded-lg bg-gov-blue px-4 py-3 text-white">
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
        <p className="text-sm leading-6">{message.text}</p>
        <p className="mt-3 text-sm font-semibold">Silakan hubungi petugas layanan KI Kanwil Kemenkum NTB untuk tindak lanjut.</p>
        <RatingControls message={message} onRating={onRating} />
      </div>
    )
  }

  return (
    <div className="flex justify-start">
      <div className="max-w-[86%] rounded-lg border border-gov-line bg-white px-4 py-3 shadow-sm">
        <div className="mb-2 flex items-center gap-2 text-xs font-bold text-gov-teal">
          <Bot size={16} aria-hidden="true" />
          AI SIKAP-KI
        </div>
        <p className="whitespace-pre-line text-sm leading-6 text-slate-800">{message.text}</p>
        {message.sources?.length ? (
          <div className="mt-3 rounded-md bg-gov-paper p-3">
            <p className="text-xs font-bold uppercase tracking-wide text-gov-navy">Sumber dokumen</p>
            <div className="mt-2 flex flex-wrap gap-2">
              {message.sources.map((source) => (
                <span key={source.judul} className="rounded-md border border-gov-line bg-white px-2 py-1 text-xs text-slate-700">
                  {source.judul}
                </span>
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
