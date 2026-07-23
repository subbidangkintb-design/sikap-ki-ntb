import { useCallback, useEffect, useState } from 'react'
import { CheckCircle2, Clock3, Loader2, RefreshCw, UserCheck } from 'lucide-react'
import { useParams } from 'react-router-dom'
import PageHeader from '../components/PageHeader.jsx'
import StatusNotice from '../components/StatusNotice.jsx'
import FormattedResponse from '../components/FormattedResponse.jsx'
import { getStatusKonsultasi } from '../lib/api.js'

const steps = [
  ['menunggu', 'Menunggu petugas', Clock3],
  ['diproses', 'Sedang ditangani', UserCheck],
  ['selesai', 'Selesai', CheckCircle2],
]

export default function ConsultationStatusPage() {
  const { pelacakanId } = useParams()
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      setData(await getStatusKonsultasi(pelacakanId))
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }, [pelacakanId])

  useEffect(() => { load() }, [load])

  const activeIndex = Math.max(0, steps.findIndex(([status]) => status === data?.status))
  return (
    <>
      <PageHeader eyebrow="Tindak lanjut Helpdesk KI" title="Pantau konsultasi Anda" description="Status ini menunjukkan proses penanganan oleh petugas tanpa menampilkan data pribadi atau catatan internal." />
      <section className="mx-auto max-w-4xl px-4 py-10">
        {loading ? <div className="flex items-center justify-center gap-3 rounded-2xl border border-gov-line bg-white p-10"><Loader2 className="animate-spin text-gov-teal" /> Memuat status konsultasi...</div> : null}
        {error ? <StatusNotice tone="error" title="Status konsultasi tidak ditemukan">{error}</StatusNotice> : null}
        {data && !loading ? (
          <div className="space-y-5">
            <div className="rounded-2xl border border-gov-line bg-white p-6 shadow-soft">
              <div className="flex flex-wrap items-start justify-between gap-4">
                <div><p className="text-xs font-bold uppercase tracking-wider text-slate-500">Nomor konsultasi</p><h2 className="mt-1 text-2xl font-black text-gov-navy">{data.kode_konsultasi}</h2></div>
                <button type="button" onClick={load} className="inline-flex items-center gap-2 rounded-lg border border-gov-line px-3 py-2 text-sm font-bold text-gov-blue"><RefreshCw size={16} /> Perbarui</button>
              </div>
              <div className="mt-7 grid gap-3 sm:grid-cols-3">
                {steps.map(([status, label, Icon], index) => {
                  const reached = index <= activeIndex
                  return <div key={status} className={`rounded-xl border p-4 ${reached ? 'border-emerald-300 bg-emerald-50 text-emerald-900' : 'border-gov-line bg-slate-50 text-slate-500'}`}><Icon size={22} /><p className="mt-2 font-black">{label}</p></div>
                })}
              </div>
              <dl className="mt-6 grid gap-4 text-sm sm:grid-cols-2">
                <StatusItem label="Status saat ini" value={data.status_label} />
                <StatusItem label="Prioritas" value={data.prioritas} />
                <StatusItem label="Dikirim" value={formatDateTime(data.dibuat_pada)} />
                <StatusItem label="Target tindak lanjut" value={formatDateTime(data.batas_tindak_lanjut)} />
              </dl>
            </div>
            {data.jawaban_petugas ? <div className="rounded-2xl border border-emerald-300 bg-emerald-50 p-6"><p className="font-black text-emerald-950">Jawaban atau koreksi petugas</p><FormattedResponse text={data.jawaban_petugas} className="mt-3 text-sm text-emerald-950" /></div> : <StatusNotice title="Belum ada jawaban petugas">Simpan tautan ini dan periksa kembali sesuai target tindak lanjut yang tertera.</StatusNotice>}
          </div>
        ) : null}
      </section>
    </>
  )
}

function StatusItem({ label, value }) {
  return <div><dt className="text-xs font-bold uppercase tracking-wide text-slate-500">{label}</dt><dd className="mt-1 font-bold text-gov-navy">{value || 'Belum tersedia'}</dd></div>
}

function formatDateTime(value) {
  if (!value) return 'Belum tersedia'
  return new Date(value).toLocaleString('id-ID', { timeZone: 'Asia/Makassar', dateStyle: 'medium', timeStyle: 'short' }) + ' WITA'
}
