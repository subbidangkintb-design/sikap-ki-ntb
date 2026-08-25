import { useEffect, useState } from 'react'
import { ArrowRight, BookOpen, ExternalLink, FileQuestion, Landmark, Lightbulb, Loader2, Search, ShieldCheck } from 'lucide-react'
import PageHeader from '../components/PageHeader.jsx'
import StatusNotice from '../components/StatusNotice.jsx'
import { getFaq, unwrapResults } from '../lib/api.js'
import { HELPDESK_PHONE_DISPLAY, HELPDESK_WHATSAPP_URL, OFFICIAL_LINKS } from '../config/service.js'

const serviceCards = [
  { title: 'Merek', text: 'Pelindungan tanda pembeda untuk barang dan/atau jasa.', href: OFFICIAL_LINKS.merek, icon: ShieldCheck, updated: '25 Agustus 2026' },
  { title: 'Hak Cipta', text: 'Informasi pencatatan ciptaan dan produk hak terkait.', href: OFFICIAL_LINKS.hakCipta, icon: BookOpen, updated: '25 Agustus 2026' },
  { title: 'Paten', text: 'Pelindungan invensi melalui dokumen teknis dan klaim.', href: OFFICIAL_LINKS.paten, icon: Lightbulb, updated: '25 Agustus 2026' },
  { title: 'Desain Industri', text: 'Pelindungan tampilan estetis suatu produk.', href: OFFICIAL_LINKS.desainIndustri, icon: Landmark, updated: '25 Agustus 2026' },
]

export default function InformationCenterPage() {
  const [faq, setFaq] = useState([])
  const [query, setQuery] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let mounted = true
    setLoading(true)
    setError('')
    const timer = window.setTimeout(() => {
      getFaq({ q: query }).then((data) => mounted && setFaq(unwrapResults(data))).catch((err) => mounted && setError(err.message)).finally(() => mounted && setLoading(false))
    }, query.trim() ? 300 : 0)
    return () => { mounted = false; window.clearTimeout(timer) }
  }, [query])

  const results = query.trim() ? faq : faq.slice(0, 6)

  return (
    <>
      <PageHeader
        eyebrow="Pusat informasi KI"
        title="Informasi resmi, terarah, dan mudah dipahami"
        description="Temukan jalur layanan, persyaratan awal, jawaban umum, serta akses langsung ke kanal resmi DJKI dan Helpdesk Kanwil Kementerian Hukum NTB."
      />
      <section className="mx-auto max-w-7xl space-y-10 px-4 py-10">
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          {serviceCards.map(({ title, text, href, icon: Icon, updated }) => (
            <a key={title} href={href} target="_blank" rel="noreferrer" className="group rounded-2xl border border-gov-line bg-white p-5 shadow-soft transition hover:-translate-y-1 hover:border-gov-blue hover:shadow-ministry">
              <span className="flex h-12 w-12 items-center justify-center rounded-xl bg-blue-50 text-gov-blue group-hover:bg-gov-blue group-hover:text-white"><Icon size={24} /></span>
              <h2 className="mt-5 text-xl font-black text-gov-navy">{title}</h2>
              <p className="mt-2 min-h-12 text-sm leading-6 text-slate-600">{text}</p>
              <p className="mt-2 text-xs text-slate-500">Diperbarui: {updated}</p>
              <span className="mt-5 inline-flex items-center gap-2 text-sm font-extrabold text-gov-blue">Informasi DJKI <ExternalLink size={15} /></span>
            </a>
          ))}
        </div>

        <div className="overflow-hidden rounded-2xl bg-gov-royal text-white shadow-ministry">
          <div className="grid lg:grid-cols-[1fr_0.45fr]">
            <div className="p-7 md:p-9">
              <p className="text-sm font-bold uppercase tracking-widest text-gov-gold">Butuh arahan petugas?</p>
              <h2 className="mt-3 text-3xl font-black">Helpdesk Kanwil siap mengarahkan layanan KI</h2>
              <p className="mt-4 max-w-2xl leading-7 text-blue-100">Sampaikan jenis layanan dan kendala Anda. Petugas Kanwil akan memberikan arahan kanal atau langkah layanan yang sesuai.</p>
              <a href={HELPDESK_WHATSAPP_URL} target="_blank" rel="noreferrer" className="mt-6 inline-flex min-h-12 items-center gap-3 rounded-xl bg-gov-gold px-5 font-black text-gov-navy hover:bg-yellow-300">
                WhatsApp {HELPDESK_PHONE_DISPLAY} <ArrowRight size={19} />
              </a>
            </div>
            <div className="flex items-center justify-center border-t border-white/10 bg-white/5 p-8 lg:border-l lg:border-t-0">
              <div className="text-center">
                <p className="text-sm font-bold uppercase tracking-widest text-blue-200">Jam layanan</p>
                <p className="mt-3 text-2xl font-black">Senin-Jumat</p>
                <p className="mt-1 text-blue-100">08.00-16.00 WITA</p>
              </div>
            </div>
          </div>
        </div>

        <div>
          <div className="max-w-2xl">
            <p className="text-sm font-extrabold uppercase tracking-wider text-gov-blue">Penelusuran informasi</p>
            <h2 className="gold-rule mt-2 text-3xl font-black text-gov-navy">Cari jawaban layanan</h2>
          </div>
          <div className="relative mt-7 max-w-3xl">
            <Search className="absolute left-4 top-4 text-slate-400" size={21} />
            <input value={query} onChange={(event) => setQuery(event.target.value)} className="min-h-14 w-full rounded-xl border border-gov-line bg-white pl-12 pr-4 shadow-soft outline-none focus:border-gov-blue focus:ring-4 focus:ring-blue-100" placeholder="Cari biaya, syarat, merek, hak cipta, paten..." />
          </div>
          {error ? <div className="mt-5"><StatusNotice tone="error" title="Informasi belum termuat">{error}</StatusNotice></div> : null}
          {loading ? <div className="mt-8 flex items-center gap-3 text-slate-600"><Loader2 className="animate-spin" /> Memuat informasi...</div> : (
            <div className="mt-6 grid gap-4 lg:grid-cols-2">
              {results.map((item) => (
                <article key={item.id} className="rounded-2xl border border-gov-line bg-white p-5 shadow-soft">
                  <div className="flex gap-3">
                    <FileQuestion className="mt-1 shrink-0 text-gov-blue" size={21} />
                    <div>
                      <p className="text-xs font-bold uppercase tracking-wider text-gov-teal">{item.kategori_nama || 'Informasi KI'}</p>
                      <h3 className="mt-2 font-black leading-7 text-gov-navy">{item.pertanyaan}</h3>
                      <p className="mt-3 whitespace-pre-line text-sm leading-7 text-slate-600">{item.jawaban}</p>
                      <div className="mt-4 flex flex-wrap items-center gap-3 border-t border-gov-line pt-3 text-xs text-slate-500">
                        <span>Ditinjau: {formatDate(item.divalidasi_pada)}</span>
                        {item.sumber_url ? <a href={item.sumber_url} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 font-bold text-gov-blue hover:underline">Buka sumber resmi <ExternalLink size={13} /></a> : <span className="font-semibold text-gov-teal">Basis pengetahuan internal terverifikasi</span>}
                      </div>
                    </div>
                  </div>
                </article>
              ))}
              {!results.length ? <div className="rounded-2xl border border-dashed border-gov-line bg-white p-8 text-center text-slate-600 lg:col-span-2">Belum ditemukan informasi yang cocok. Coba kata kunci lain atau gunakan Chatbot Helpdesk KI.</div> : null}
            </div>
          )}
        </div>
      </section>
    </>
  )
}

function formatDate(value) {
  if (!value) return 'belum tercatat'
  return new Date(value).toLocaleDateString('id-ID', { timeZone: 'Asia/Makassar', year: 'numeric', month: 'short', day: 'numeric' })
}

