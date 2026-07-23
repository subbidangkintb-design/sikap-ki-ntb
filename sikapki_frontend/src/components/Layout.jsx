import { useEffect, useState } from 'react'
import { Link, NavLink, useLocation } from 'react-router-dom'
import {
  ArrowUp, BarChart3, BotMessageSquare, Clock3, ClipboardCheck, ExternalLink,
  Home, Library, Mail, MapPin, Menu, MessageCircle, Phone, SearchCheck, ShieldCheck, X,
} from 'lucide-react'
import logo from '../assets/sikap-ki-ntb-logo-2026.png'
import AccessibilityPanel from './AccessibilityPanel.jsx'
import {
  HELPDESK_EMAIL, HELPDESK_PHONE_DISPLAY, HELPDESK_WHATSAPP_URL,
  KANWIL_ADDRESS, KANWIL_MAPS_URL, OFFICIAL_LINKS, SERVICE_HOURS,
} from '../config/service.js'

const navItems = [
  { to: '/', label: 'Beranda', icon: Home, end: true },
  { to: '/cek-merek', label: 'Penelusuran Merek', icon: SearchCheck },
  { to: '/chatbot', label: 'Chatbot Helpdesk', icon: BotMessageSquare },
  { to: '/checklist', label: 'Checklist', icon: ClipboardCheck },
  { to: '/informasi', label: 'Pusat Informasi', icon: Library },
  { to: '/statistik', label: 'Statistik', icon: BarChart3 },
]

const footerServices = [
  { to: '/cek-merek', label: 'Asisten penelusuran awal merek' },
  { to: '/chatbot', label: 'Chatbot Helpdesk KI' },
  { to: '/checklist', label: 'Checklist dokumen' },
  { to: '/informasi', label: 'Pusat informasi' },
  { to: '/statistik', label: 'Statistik layanan' },
  { to: '/uji-coba', label: 'Evaluasi pengalaman pengguna' },
]

const officialServices = [
  { href: OFFICIAL_LINKS.pdki, label: 'Pangkalan Data KI' },
  { href: OFFICIAL_LINKS.skm, label: 'Klasifikasi Merek DJKI' },
  { href: OFFICIAL_LINKS.merek, label: 'Persyaratan merek' },
  { href: OFFICIAL_LINKS.hakCipta, label: 'Persyaratan hak cipta' },
  { href: OFFICIAL_LINKS.paten, label: 'Persyaratan paten' },
  { href: OFFICIAL_LINKS.kanwil, label: 'Website Kanwil NTB' },
]

export default function Layout({ children }) {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)
  const { pathname } = useLocation()

  useEffect(() => {
    setMobileMenuOpen(false)
    window.requestAnimationFrame(() => {
      document.getElementById('main-content')?.focus({ preventScroll: true })
      window.scrollTo({ top: 0, behavior: 'auto' })
    })
  }, [pathname])

  useEffect(() => {
    if (!mobileMenuOpen) return undefined

    const closeOnEscape = (event) => {
      if (event.key === 'Escape') setMobileMenuOpen(false)
    }

    window.addEventListener('keydown', closeOnEscape)
    return () => window.removeEventListener('keydown', closeOnEscape)
  }, [mobileMenuOpen])

  return (
    <div className="min-h-screen bg-gov-paper text-gov-navy">
      <a href="#main-content" className="skip-link">Lewati ke konten utama</a>
      <header className="sticky top-0 z-40 border-b border-gov-line bg-white/95 backdrop-blur">
        <div className="mx-auto max-w-7xl px-4 py-2.5 sm:py-3 lg:flex lg:items-center lg:justify-between lg:gap-3">
          <div className="flex items-center justify-between gap-3">
            <Link to="/" className="flex min-w-0 items-center gap-3">
              <img src={logo} alt="Logo SIKAP-KI NTB" className="h-11 w-11 shrink-0 rounded-lg border border-slate-200 object-cover object-center sm:h-14 sm:w-14 sm:rounded-xl" />
              <div className="min-w-0">
                <p className="truncate text-base font-black leading-tight tracking-tight sm:text-lg">SIKAP-KI NTB</p>
                <p className="truncate text-xs font-medium text-slate-600 sm:text-sm">Portal Pelayanan KI Terpadu</p>
              </div>
            </Link>
            <button
              type="button"
              className="inline-flex h-11 w-11 shrink-0 items-center justify-center rounded-xl border border-gov-line bg-white text-gov-navy transition hover:bg-slate-50 focus:outline-none focus:ring-4 focus:ring-gov-mint lg:hidden"
              aria-expanded={mobileMenuOpen}
              aria-controls="main-navigation"
              aria-label={mobileMenuOpen ? 'Tutup menu navigasi' : 'Buka menu navigasi'}
              onClick={() => setMobileMenuOpen((open) => !open)}
            >
              {mobileMenuOpen ? <X size={23} aria-hidden="true" /> : <Menu size={23} aria-hidden="true" />}
            </button>
          </div>
          <nav
            id="main-navigation"
            className={`${mobileMenuOpen ? 'grid' : 'hidden'} mt-3 grid-cols-1 gap-1 border-t border-gov-line pt-3 sm:grid-cols-2 lg:mt-0 lg:flex lg:border-0 lg:pt-0`}
            aria-label="Navigasi utama"
          >
            {navItems.map(({ to, label, icon: Icon, end }) => (
              <NavLink
                key={to}
                to={to}
                end={end}
                className={({ isActive }) =>
                  [
                    'inline-flex min-h-11 items-center gap-3 rounded-lg border px-3 text-sm font-bold transition lg:min-h-10 lg:shrink-0 lg:gap-2',
                    isActive
                      ? 'border-gov-gold bg-amber-50 text-gov-navy'
                      : 'border-transparent text-slate-700 hover:border-gov-line hover:bg-slate-50',
                  ].join(' ')
                }
              >
                <Icon size={18} aria-hidden="true" />
                {label}
              </NavLink>
            ))}
          </nav>
        </div>
      </header>
      <main id="main-content" tabIndex="-1" className="focus:outline-none">{children}</main>
      <AccessibilityPanel />
      <footer className="border-t-4 border-gov-gold bg-gov-navy text-white">
        <div className="border-b border-white/10 bg-gov-royal">
          <div className="mx-auto flex max-w-7xl flex-col gap-4 px-4 py-5 sm:flex-row sm:items-center sm:justify-between">
            <div className="flex items-center gap-3">
              <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-gov-gold text-gov-navy"><MessageCircle size={22} aria-hidden="true" /></span>
              <div>
                <p className="font-black">Masih membutuhkan arahan layanan KI?</p>
                <p className="mt-1 text-sm text-blue-100">Petugas Helpdesk KI Kanwil NTB siap membantu pada jam layanan.</p>
              </div>
            </div>
            <a href={HELPDESK_WHATSAPP_URL} target="_blank" rel="noreferrer" className="inline-flex min-h-12 items-center justify-center gap-2 rounded-xl bg-[#128c4a] px-5 text-sm font-black text-white shadow-lg transition hover:bg-[#0f7a40] focus:outline-none focus:ring-4 focus:ring-white/30">
              <MessageCircle size={19} aria-hidden="true" /> Konsultasi via WhatsApp
            </a>
          </div>
        </div>

        <div className="mx-auto grid max-w-7xl gap-9 px-4 py-10 text-sm sm:grid-cols-2 lg:grid-cols-[1.35fr_0.8fr_0.85fr_1.25fr]">
          <section aria-labelledby="footer-identity">
            <div className="flex items-center gap-4">
              <img src={logo} alt="Logo SIKAP-KI NTB" className="h-20 w-20 rounded-2xl border-2 border-white/20 bg-white object-cover shadow-lg" />
              <div>
                <p id="footer-identity" className="text-lg font-black">SIKAP-KI NTB</p>
                <p className="mt-1 text-xs font-bold uppercase tracking-wider text-gov-gold">Portal Pelayanan KI Terpadu</p>
              </div>
            </div>
            <p className="mt-5 max-w-sm leading-7 text-blue-100">Sistem Informasi dan Konsultasi Awal Pelayanan Kekayaan Intelektual Nusa Tenggara Barat.</p>
            <p className="mt-2 max-w-sm text-xs leading-5 text-blue-200">Portal pelayanan KI terpadu berbasis pengetahuan resmi dengan Artificial Intelligence sebagai teknologi pendukung.</p>
            <div className="mt-5 flex items-start gap-2 rounded-xl border border-white/10 bg-white/5 p-3 text-xs leading-5 text-blue-100">
              <ShieldCheck className="mt-0.5 shrink-0 text-gov-gold" size={18} aria-hidden="true" />
              Informasi sistem bersifat layanan awal. Keputusan resmi tetap mengikuti pemeriksaan DJKI dan data resmi PDKI.
            </div>
          </section>

          <section aria-labelledby="footer-services">
            <h2 id="footer-services" className="font-black text-white">Layanan SIKAP-KI</h2>
            <ul className="mt-4 space-y-3">
              {footerServices.map((item) => (
                <li key={item.to}><Link to={item.to} className="text-blue-100 transition hover:text-gov-gold hover:underline">{item.label}</Link></li>
              ))}
            </ul>
          </section>

          <section aria-labelledby="footer-official">
            <h2 id="footer-official" className="font-black text-white">Tautan Resmi</h2>
            <ul className="mt-4 space-y-3">
              {officialServices.map((item) => (
                <li key={item.href}>
                  <a href={item.href} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1.5 text-blue-100 transition hover:text-gov-gold hover:underline">
                    {item.label} <ExternalLink size={13} aria-hidden="true" />
                  </a>
                </li>
              ))}
            </ul>
          </section>

          <section aria-labelledby="footer-contact">
            <h2 id="footer-contact" className="font-black text-white">Kontak Kantor Wilayah</h2>
            <address className="mt-4 space-y-4 not-italic text-blue-100">
              <a href={KANWIL_MAPS_URL} target="_blank" rel="noreferrer" className="flex items-start gap-3 transition hover:text-gov-gold">
                <MapPin className="mt-0.5 shrink-0" size={18} aria-hidden="true" /><span className="leading-6">{KANWIL_ADDRESS}</span>
              </a>
              <a href="tel:+62818182444" className="flex items-center gap-3 transition hover:text-gov-gold"><Phone className="shrink-0" size={18} aria-hidden="true" />{HELPDESK_PHONE_DISPLAY}</a>
              <a href={`mailto:${HELPDESK_EMAIL}`} className="flex items-center gap-3 break-all transition hover:text-gov-gold"><Mail className="shrink-0" size={18} aria-hidden="true" />{HELPDESK_EMAIL}</a>
              <p className="flex items-start gap-3"><Clock3 className="mt-0.5 shrink-0" size={18} aria-hidden="true" /><span>{SERVICE_HOURS}</span></p>
            </address>
          </section>
        </div>

        <div className="border-t border-white/10">
          <div className="mx-auto flex max-w-7xl flex-col gap-3 px-4 py-5 text-xs text-blue-200 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <p>© {new Date().getFullYear()} Kantor Wilayah Kementerian Hukum Nusa Tenggara Barat.</p>
              <p className="mt-1">Data klasifikasi: © WIPO, Nice Classification NCL 13-2026.</p>
            </div>
            <div className="flex flex-wrap items-center gap-x-5 gap-y-2">
              <a href={OFFICIAL_LINKS.kontak} target="_blank" rel="noreferrer" className="hover:text-white hover:underline">Kontak resmi</a>
              <span>Aksesibilitas dan layanan publik</span>
              <button type="button" onClick={() => window.scrollTo({ top: 0, behavior: 'smooth' })} className="inline-flex items-center gap-1 font-bold text-white hover:text-gov-gold" aria-label="Kembali ke bagian atas halaman">Kembali ke atas <ArrowUp size={14} /></button>
            </div>
          </div>
        </div>
      </footer>
    </div>
  )
}
