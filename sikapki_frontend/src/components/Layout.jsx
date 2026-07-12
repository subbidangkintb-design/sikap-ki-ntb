import { Link, NavLink } from 'react-router-dom'
import { FileQuestion, MessageSquareText, SearchCheck, ShieldCheck } from 'lucide-react'

const navItems = [
  { to: '/cek-merek', label: 'Cek Merek', icon: SearchCheck },
  { to: '/chatbot', label: 'Tanya AI', icon: MessageSquareText },
  { to: '/faq', label: 'FAQ', icon: FileQuestion },
]

export default function Layout({ children }) {
  return (
    <div className="min-h-screen bg-gov-paper text-gov-navy">
      <header className="border-b border-gov-line bg-white">
        <div className="mx-auto flex max-w-6xl flex-col gap-4 px-4 py-4 md:flex-row md:items-center md:justify-between">
          <Link to="/" className="flex items-center gap-3">
            <div className="flex h-11 w-11 items-center justify-center rounded-lg bg-gov-navy text-white">
              <ShieldCheck size={25} aria-hidden="true" />
            </div>
            <div>
              <p className="text-lg font-bold leading-tight">SIKAP-KI NTB</p>
              <p className="text-sm text-slate-600">Asisten Kekayaan Intelektual</p>
            </div>
          </Link>
          <nav className="flex flex-wrap gap-2">
            {navItems.map(({ to, label, icon: Icon }) => (
              <NavLink
                key={to}
                to={to}
                className={({ isActive }) =>
                  [
                    'inline-flex min-h-11 items-center gap-2 rounded-md border px-4 text-sm font-semibold transition',
                    isActive
                      ? 'border-gov-teal bg-gov-mint text-gov-navy'
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
      <main>{children}</main>
      <footer className="border-t border-gov-line bg-white">
        <div className="mx-auto flex max-w-6xl flex-col gap-2 px-4 py-6 text-sm text-slate-600 md:flex-row md:items-center md:justify-between">
          <p>Kanwil Kemenkum NTB - layanan informasi awal Kekayaan Intelektual.</p>
          <p>Keputusan resmi tetap mengikuti pemeriksaan DJKI/PDKI.</p>
        </div>
      </footer>
    </div>
  )
}
