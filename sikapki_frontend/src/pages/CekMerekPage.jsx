import { useMemo, useState } from 'react'
import { Loader2, SearchCheck } from 'lucide-react'
import PageHeader from '../components/PageHeader.jsx'
import StatusNotice from '../components/StatusNotice.jsx'
import { cekMerek } from '../lib/api.js'

const riskStyles = {
  rendah: 'border-emerald-200 bg-emerald-50 text-emerald-900',
  sedang: 'border-amber-200 bg-amber-50 text-amber-900',
  tinggi: 'border-red-200 bg-red-50 text-red-900',
}

export default function CekMerekPage() {
  const [form, setForm] = useState({ nama_merek: '', deskripsi_produk: '' })
  const [result, setResult] = useState(null)
  const [error, setError] = useState('')
  const [isLoading, setIsLoading] = useState(false)

  const loadingSteps = useMemo(() => [
    'Menganalisis deskripsi produk/jasa',
    'Mengusulkan kelas Nice',
    'Membandingkan nama dengan data merek',
    'Menyusun saran naratif',
  ], [])

  async function handleSubmit(event) {
    event.preventDefault()
    setError('')
    setResult(null)
    setIsLoading(true)
    try {
      const data = await cekMerek(form)
      setResult(data)
    } catch (err) {
      setError(err.message)
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <>
      <PageHeader
        eyebrow="AI Cek & Saran Merek"
        title="Cek risiko awal nama merek"
        description="Masukkan nama merek dan deskripsi produk atau jasa. Sistem akan membantu memperkirakan kelas Nice, mencari kemiripan, dan memberi saran awal."
      />
      <section className="mx-auto grid max-w-6xl gap-6 px-4 py-8 lg:grid-cols-[0.95fr_1.05fr]">
        <form onSubmit={handleSubmit} className="rounded-lg border border-gov-line bg-white p-5 shadow-soft">
          <div className="space-y-5">
            <div>
              <label htmlFor="nama_merek" className="block text-sm font-bold text-gov-navy">Nama merek</label>
              <input
                id="nama_merek"
                value={form.nama_merek}
                onChange={(event) => setForm({ ...form, nama_merek: event.target.value })}
                className="mt-2 min-h-12 w-full rounded-md border border-gov-line px-3 outline-none focus:border-gov-teal focus:ring-2 focus:ring-gov-mint"
                placeholder="Contoh: Kopi Kita"
                required
              />
            </div>
            <div>
              <label htmlFor="deskripsi_produk" className="block text-sm font-bold text-gov-navy">Deskripsi produk/jasa</label>
              <textarea
                id="deskripsi_produk"
                value={form.deskripsi_produk}
                onChange={(event) => setForm({ ...form, deskripsi_produk: event.target.value })}
                className="mt-2 min-h-40 w-full rounded-md border border-gov-line px-3 py-3 outline-none focus:border-gov-teal focus:ring-2 focus:ring-gov-mint"
                placeholder="Contoh: produk kopi bubuk dan minuman kopi siap saji"
                required
              />
            </div>
            <button
              type="submit"
              disabled={isLoading}
              className="inline-flex min-h-14 w-full items-center justify-center gap-3 rounded-lg bg-gov-teal px-5 text-base font-bold text-white transition hover:bg-teal-700 disabled:cursor-not-allowed disabled:bg-slate-400"
            >
              {isLoading ? <Loader2 className="h-5 w-5 animate-spin" aria-hidden="true" /> : <SearchCheck size={21} aria-hidden="true" />}
              {isLoading ? 'Memproses pengecekan' : 'Cek Nama Merek'}
            </button>
          </div>
        </form>

        <div className="space-y-4">
          {error ? (
            <StatusNotice tone="error" title="Pengecekan belum berhasil">
              {error}
            </StatusNotice>
          ) : null}

          {isLoading ? (
            <div className="rounded-lg border border-gov-line bg-white p-5 shadow-soft">
              <p className="font-bold text-gov-navy">Sedang memproses</p>
              <div className="mt-4 grid gap-3">
                {loadingSteps.map((step) => (
                  <div key={step} className="flex items-center gap-3 rounded-md bg-gov-paper p-3 text-sm text-slate-700">
                    <Loader2 className="h-4 w-4 animate-spin text-gov-teal" aria-hidden="true" />
                    {step}
                  </div>
                ))}
              </div>
            </div>
          ) : null}

          {!result && !isLoading ? (
            <StatusNotice title="Hasil akan tampil di sini">
              Setelah formulir dikirim, sistem akan menampilkan kelas Nice, merek mirip, skor risiko, saran, dan disclaimer.
            </StatusNotice>
          ) : null}

          {result ? <CekMerekResult result={result} /> : null}
        </div>
      </section>
    </>
  )
}

function CekMerekResult({ result }) {
  const risk = result.skor_risiko || 'rendah'
  return (
    <div className="space-y-4">
      <div className="rounded-lg border border-gov-line bg-white p-5 shadow-soft">
        <p className="text-sm font-bold uppercase tracking-wide text-gov-teal">Kelas Nice terdeteksi</p>
        <div className="mt-3 flex flex-wrap gap-2">
          {(result.kelas_nice_terdeteksi || []).map((kelas) => (
            <span key={kelas} className="rounded-md bg-gov-mint px-3 py-2 text-sm font-bold text-gov-navy">Kelas {kelas}</span>
          ))}
        </div>
      </div>

      <div className={`rounded-lg border p-5 ${riskStyles[risk] || riskStyles.rendah}`}>
        <p className="text-sm font-bold uppercase tracking-wide">Skor risiko</p>
        <p className="mt-2 text-3xl font-bold capitalize">{risk}</p>
      </div>

      <div className="rounded-lg border border-gov-line bg-white p-5 shadow-soft">
        <p className="font-bold text-gov-navy">Merek mirip</p>
        {(result.merek_mirip || []).length ? (
          <div className="mt-3 overflow-x-auto">
            <table className="w-full min-w-[560px] border-collapse text-left text-sm">
              <thead className="bg-gov-paper text-gov-navy">
                <tr>
                  <th className="border-b border-gov-line px-3 py-3">Nama</th>
                  <th className="border-b border-gov-line px-3 py-3">Kelas</th>
                  <th className="border-b border-gov-line px-3 py-3">Status</th>
                  <th className="border-b border-gov-line px-3 py-3">Skor</th>
                </tr>
              </thead>
              <tbody>
                {result.merek_mirip.map((item) => (
                  <tr key={`${item.nama}-${item.kelas}-${item.skor_kemiripan}`}>
                    <td className="border-b border-gov-line px-3 py-3 font-semibold">{item.nama}</td>
                    <td className="border-b border-gov-line px-3 py-3">{item.kelas}</td>
                    <td className="border-b border-gov-line px-3 py-3">{item.status}</td>
                    <td className="border-b border-gov-line px-3 py-3 font-bold">{item.skor_kemiripan}%</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="mt-3 text-sm leading-6 text-slate-700">Tidak ditemukan merek mirip di atas ambang kemiripan.</p>
        )}
      </div>

      <div className="rounded-lg border border-gov-line bg-white p-5 shadow-soft">
        <p className="font-bold text-gov-navy">Saran naratif</p>
        <div className="prose-answer mt-3 whitespace-pre-line text-sm leading-7 text-slate-700">{result.saran_naratif}</div>
      </div>

      <StatusNotice tone="warning" title="Disclaimer penting">
        {result.disclaimer}
      </StatusNotice>
    </div>
  )
}
