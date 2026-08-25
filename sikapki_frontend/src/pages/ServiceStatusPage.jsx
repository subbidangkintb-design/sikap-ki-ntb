import { useEffect, useState } from 'react'
import { CheckCircle2, Clock3, RefreshCw, TriangleAlert } from 'lucide-react'
import PageHeader from '../components/PageHeader.jsx'
import StatusNotice from '../components/StatusNotice.jsx'
import { getStatusLayanan } from '../lib/api.js'

export default function ServiceStatusPage() {
  const [status, setStatus] = useState(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)
  async function refresh() { setLoading(true); setError(''); try { setStatus(await getStatusLayanan()) } catch (err) { setError(err.message) } finally { setLoading(false) } }
  useEffect(() => { refresh() }, [])
  const healthy = status?.status === 'sehat'
  return <>
    <PageHeader eyebrow="Status layanan" title="Pantau kesiapan layanan SIKAP-KI NTB" description="Kondisi database, AI, dokumen terverifikasi, dan data pembanding ditampilkan secara ringkas." />
    <section className="mx-auto max-w-5xl px-4 py-10">
      {error ? <StatusNotice tone="error" title="Status layanan belum dapat diperiksa">{error}</StatusNotice> : null}
      <div className={`rounded-2xl border p-6 ${healthy ? 'border-emerald-200 bg-emerald-50' : 'border-amber-200 bg-amber-50'}`}><div className="flex items-start gap-4">{healthy ? <CheckCircle2 className="text-emerald-700" size={30} /> : <TriangleAlert className="text-amber-700" size={30} />}<div><h2 className="text-xl font-black">{loading ? 'Memeriksa layanan...' : healthy ? 'Layanan berjalan normal' : 'Sebagian layanan perlu perhatian'}</h2><p className="mt-1 text-sm leading-6">{status?.diperiksa_pada ? `Pemeriksaan terakhir: ${new Date(status.diperiksa_pada).toLocaleString('id-ID')}` : 'Silakan coba perbarui pemeriksaan.'}</p></div></div></div>
      <div className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4"><StatusCard label="Database" value={status?.database ? 'Normal' : 'Gangguan'} ok={status?.database} /><StatusCard label="Layanan AI" value={status?.ai_terkonfigurasi ? 'Terkonfigurasi' : 'Perlu perhatian'} ok={status?.ai_terkonfigurasi} /><StatusCard label="Dokumen resmi" value={status?.dokumen_terverifikasi ?? '-'} ok /><StatusCard label="Data pembanding" value={status?.data_pembanding ?? '-'} ok /></div>
      <button type="button" onClick={refresh} className="mt-6 inline-flex min-h-11 items-center gap-2 rounded-xl bg-gov-royal px-4 text-sm font-black text-white hover:bg-blue-900"><RefreshCw size={17} /> Periksa kembali</button>
      <p className="mt-5 flex items-start gap-2 text-sm leading-6 text-slate-600"><Clock3 className="mt-0.5 shrink-0" size={17} />Jika gangguan berlanjut, gunakan kanal Helpdesk KI resmi pada bagian kontak portal.</p>
    </section>
  </>
}
function StatusCard({ label, value, ok }) { return <div className="rounded-xl border border-gov-line bg-white p-4 shadow-soft"><p className="text-xs font-black uppercase tracking-wide text-slate-500">{label}</p><p className={`mt-2 text-lg font-black ${ok ? 'text-emerald-700' : 'text-amber-700'}`}>{value}</p></div> }
