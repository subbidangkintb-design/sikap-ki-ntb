import { Link } from 'react-router-dom'
import { ArrowRight, BarChart3, BotMessageSquare, CheckCircle2, ClipboardCheck, History, LayoutDashboard, SearchCheck, ShieldCheck } from 'lucide-react'
import logo from '../assets/sikap-ki-ntb-logo-2026.png'

const services = [
  { to: '/', title: 'Prototipe SIKAP-KI NTB', text: 'Sarana pendukung model tata kelola konsultasi awal KI yang terintegrasi dan terstandar.', icon: ShieldCheck, accent: 'bg-indigo-50 text-indigo-700' },
  { to: '/chatbot', title: 'Chatbot Helpdesk KI', text: 'Jawaban awal berdasarkan dokumen terverifikasi, disertai sumber dan mekanisme eskalasi.', icon: BotMessageSquare, accent: 'bg-emerald-50 text-emerald-700' },
  { to: '/cek-merek', title: 'Asisten Penelusuran Awal Merek', text: 'Lihat kelas Nice dan indikasi kemiripan pada data publikasi resmi DJKI yang tersedia.', icon: SearchCheck, accent: 'bg-blue-50 text-gov-blue' },
  { to: '/checklist', title: 'Checklist dokumen', text: 'Siapkan persyaratan awal secara interaktif sebelum menuju sistem permohonan resmi.', icon: ClipboardCheck, accent: 'bg-amber-50 text-amber-700' },
  { title: 'Riwayat konsultasi', text: 'Interaksi dan tindak lanjut petugas tercatat dengan akses terbatas untuk evaluasi layanan.', icon: History, accent: 'bg-violet-50 text-violet-700' },
  { to: '/statistik', title: 'Dashboard statistik layanan', text: 'Data agregat membantu monitoring, evaluasi, dan penyempurnaan kebijakan pelayanan.', icon: LayoutDashboard, accent: 'bg-rose-50 text-rose-700' },
]

export default function HomePage() {
  return (
    <>
      <section className="ministry-grid relative overflow-hidden bg-white">
        <div className="absolute inset-x-0 top-0 h-1.5 bg-gradient-to-r from-gov-royal via-gov-gold to-gov-royal" />
        <div className="mx-auto grid max-w-7xl gap-10 px-4 py-14 lg:grid-cols-[1.1fr_0.9fr] lg:items-center lg:py-20">
          <div>
            <div className="inline-flex items-center gap-2 rounded-full border border-blue-200 bg-blue-50 px-4 py-2 text-xs font-extrabold uppercase tracking-wider text-gov-royal">
              <ShieldCheck size={16} /> Kanwil Kementerian Hukum NTB
            </div>
            <h1 className="mt-6 max-w-4xl text-4xl font-black leading-[1.08] tracking-tight text-gov-navy md:text-6xl">
              Layanan KI lebih jelas, <span className="text-gov-blue">terarah</span>, dan mudah dijangkau
            </h1>
            <p className="mt-6 max-w-2xl text-lg leading-8 text-slate-600">
              SIKAP-KI NTB mendukung tata kelola konsultasi awal KI melalui pengetahuan resmi, layanan mandiri untuk kebutuhan dasar, pencatatan layanan, dan eskalasi kasus kompleks kepada petugas.
            </p>
            <div className="mt-8 flex flex-col gap-3 sm:flex-row">
              <Link to="/cek-merek" className="inline-flex min-h-14 items-center justify-center gap-3 rounded-xl bg-gov-royal px-6 font-black text-white shadow-ministry transition hover:-translate-y-0.5 hover:bg-blue-900">
                <SearchCheck size={21} /> Mulai penelusuran awal
              </Link>
              <Link to="/informasi" className="inline-flex min-h-14 items-center justify-center gap-3 rounded-xl border-2 border-gov-royal bg-white px-6 font-black text-gov-royal transition hover:bg-blue-50">
                Jelajahi pusat informasi <ArrowRight size={19} />
              </Link>
            </div>
            <div className="mt-8 flex flex-wrap gap-x-6 gap-y-3 text-sm font-semibold text-slate-600">
              <span className="flex items-center gap-2"><CheckCircle2 className="text-emerald-600" size={18} /> Sumber terverifikasi</span>
              <span className="flex items-center gap-2"><CheckCircle2 className="text-emerald-600" size={18} /> Tanpa klaim keputusan</span>
              <span className="flex items-center gap-2"><CheckCircle2 className="text-emerald-600" size={18} /> Arahan Helpdesk Kanwil</span>
            </div>
          </div>

          <div className="relative mx-auto w-full max-w-lg">
            <div className="absolute -inset-4 rotate-2 rounded-[2rem] bg-gov-gold/20" />
            <div className="relative overflow-hidden rounded-[2rem] border border-slate-200 bg-white p-5 shadow-ministry">
              <img src={logo} alt="SIKAP-KI NTB — Sistem Informasi dan Konsultasi Pelayanan Kekayaan Intelektual" className="mx-auto aspect-square w-full rounded-2xl object-cover object-center" />
              <div className="mt-4 rounded-xl bg-gov-royal p-4 text-center text-white">
                <p className="text-xs font-bold uppercase tracking-widest text-gov-gold">Portal pelayanan terpadu</p>
                <p className="mt-1 font-extrabold">Kekayaan Intelektual Nusa Tenggara Barat</p>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="border-y border-gov-line bg-gov-paper">
        <div className="mx-auto max-w-7xl px-4 py-12">
          <div className="max-w-3xl">
            <p className="text-sm font-extrabold uppercase tracking-wider text-gov-blue">Output teknologi terintegrasi</p>
            <h2 className="gold-rule mt-2 text-3xl font-black text-gov-navy md:text-4xl">Enam sarana pendukung tata kelola layanan</h2>
          </div>
          <div className="mt-9 grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            {services.map(({ to, title, text, icon: Icon, accent }) => (
              <article key={title} className="group rounded-2xl border border-gov-line bg-white p-5 shadow-soft transition hover:-translate-y-1 hover:border-gov-blue hover:shadow-ministry">
                <span className={`flex h-12 w-12 items-center justify-center rounded-xl ${accent}`}><Icon size={24} /></span>
                <h3 className="mt-5 text-lg font-black leading-7 text-gov-navy">{title}</h3>
                <p className="mt-2 text-sm leading-6 text-slate-600">{text}</p>
                {to ? <Link to={to} className="mt-5 inline-flex items-center gap-2 text-sm font-extrabold text-gov-blue">Buka layanan <ArrowRight className="transition group-hover:translate-x-1" size={16} /></Link> : <span className="mt-5 inline-flex text-xs font-bold uppercase tracking-wide text-slate-500">Akses petugas terbatas</span>}
              </article>
            ))}
          </div>
        </div>
      </section>

      <section className="bg-white">
        <div className="mx-auto grid max-w-7xl gap-8 px-4 py-12 lg:grid-cols-[0.8fr_1.2fr] lg:items-center">
          <div className="rounded-2xl bg-gov-royal p-7 text-white shadow-ministry">
            <BarChart3 className="text-gov-gold" size={34} />
            <h2 className="mt-5 text-2xl font-black">Statistik yang dapat dipertanggungjawabkan</h2>
            <p className="mt-3 leading-7 text-blue-100">Dashboard hanya menampilkan aktivitas agregat pada portal. Angka tidak diklaim sebagai keseluruhan permohonan KI di NTB.</p>
            <Link to="/statistik" className="mt-6 inline-flex items-center gap-2 font-black text-gov-gold hover:underline">Lihat statistik layanan <ArrowRight size={18} /></Link>
          </div>
          <div>
            <p className="text-sm font-extrabold uppercase tracking-wider text-gov-blue">Prinsip pelayanan</p>
            <h2 className="mt-2 text-3xl font-black text-gov-navy">Informasi awal yang aman bagi masyarakat dan institusi</h2>
            <div className="mt-6 grid gap-4 sm:grid-cols-2">
              <Principle title="Tidak menjanjikan keputusan" text="Indikator kemiripan bukan peluang diterima atau ditolak oleh DJKI." />
              <Principle title="Tidak membuat nama merek" text="Sistem tidak memberikan usulan nama merek alternatif kepada pengguna." />
              <Principle title="Fokus pada label" text="Saran diarahkan pada aspek label yang perlu ditinjau untuk memperkuat daya pembeda." />
              <Principle title="Eskalasi resmi" text="Pertanyaan yang memerlukan penanganan diarahkan ke Helpdesk KI Kanwil." />
            </div>
          </div>
        </div>
      </section>
    </>
  )
}

function Principle({ title, text }) {
  return (
    <div className="rounded-xl border border-gov-line p-4">
      <h3 className="font-extrabold text-gov-navy">{title}</h3>
      <p className="mt-2 text-sm leading-6 text-slate-600">{text}</p>
    </div>
  )
}
