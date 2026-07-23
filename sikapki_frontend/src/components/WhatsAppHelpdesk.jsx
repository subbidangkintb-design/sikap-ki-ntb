import { MessageCircle } from 'lucide-react'
import { HELPDESK_PHONE_DISPLAY, HELPDESK_WHATSAPP_URL } from '../config/service.js'

export default function WhatsAppHelpdesk() {
  return (
    <a
      href={HELPDESK_WHATSAPP_URL}
      target="_blank"
      rel="noreferrer"
      className="group fixed bottom-[max(0.75rem,env(safe-area-inset-bottom))] right-3 z-50 flex items-center gap-3 rounded-full bg-[#128c4a] p-3 text-white shadow-[0_14px_34px_rgba(18,140,74,0.35)] transition hover:-translate-y-1 hover:bg-[#0f7a40] focus:outline-none focus:ring-4 focus:ring-emerald-200 sm:bottom-5 sm:right-5 md:px-4"
      aria-label={`Konsultasi sekarang melalui WhatsApp Helpdesk KI Kanwil ${HELPDESK_PHONE_DISPLAY}`}
    >
      <span className="hidden text-left md:block">
        <span className="block text-[11px] font-semibold uppercase tracking-wider text-emerald-100">Konsultasi sekarang</span>
        <span className="block text-sm font-extrabold">Helpdesk KI Kanwil</span>
      </span>
      <span className="flex h-11 w-11 items-center justify-center rounded-full bg-white/15">
        <MessageCircle size={25} fill="currentColor" aria-hidden="true" />
      </span>
    </a>
  )
}
