import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { Activity, BarChart3, BookOpenCheck, BotMessageSquare, CheckCircle2, Clock3, Download, FileBadge2, Loader2, SearchCheck, ShieldCheck } from 'lucide-react'
import PageHeader from '../components/PageHeader.jsx'
import StatusNotice from '../components/StatusNotice.jsx'
import { getStatistikLayanan } from '../lib/api.js'

export default function DashboardPage() {
  const [stats, setStats] = useState(null)
  const [error, setError] = useState('')
  const [period, setPeriod] = useState(7)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let mounted = true
    setLoading(true)
    setError('')
    getStatistikLayanan(period)
      .then((data) => mounted && setStats(data))
      .catch((err) => mounted && setError(err.message))
      .finally(() => mounted && setLoading(false))
    return () => { mounted = false }
  }, [period])

  const trendMax = useMemo(() => stats
    ? Math.max(1, ...(stats.tren_periode || stats.tren_7_hari || []).map((item) => item.chatbot + item.cek_merek))
    : 1, [stats])

  return (
    <>
      <PageHeader
        eyebrow="Statistik layanan"
        title="Aktivitas layanan SIKAP-KI NTB"
        description="Ringkasan agregat penggunaan portal untuk membantu Kanwil melihat kebutuhan informasi masyarakat tanpa menampilkan data pribadi pengguna."
      />
      <section className="ministry-grid mx-auto max-w-7xl px-4 py-10">
        <div className="mb-6 flex flex-wrap items-center justify-between gap-3 rounded-xl border border-gov-line bg-white p-3 shadow-soft">
          <div className="flex items-center gap-2">
            {[7, 30, 90].map((days) => <button key={days} type="button" onClick={() => setPeriod(days)} className={`rounded-lg px-4 py-2 text-sm font-black ${period === days ? 'bg-gov-blue text-white' : 'bg-gov-paper text-slate-700'}`}>{days} hari</button>)}
            {loading ? <Loader2 size={18} className="animate-spin text-gov-blue" /> : null}
          </div>
          <button type="button" onClick={() => exportMonitoringCsv(stats)} disabled={!stats} className="inline-flex items-center gap-2 rounded-lg border border-gov-line px-4 py-2 text-sm font-black text-gov-blue disabled:opacity-50"><Download size={17} /> Unduh CSV</button>
        </div>
        {error ? <StatusNotice tone="error" title="Statistik belum dapat dimuat">{error}</StatusNotice> : null}
        {!stats && !error ? (
          <div className="flex min-h-52 items-center justify-center gap-3 text-slate-600">
            <Loader2 className="animate-spin text-gov-blue" /> Memuat statistik layanan...
          </div>
        ) : null}
        {stats ? (
          <div className="space-y-6">
            <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
              <StatCard icon={SearchCheck} label="Analisis klasifikasi" value={stats.cek_merek_total} note="Penggunaan asisten klasifikasi merek" />
              <StatCard icon={BotMessageSquare} label="Pertanyaan KI" value={stats.chatbot_total} note="Interaksi pada Chatbot Helpdesk KI" />
              <StatCard icon={BookOpenCheck} label="Informasi tersedia" value={stats.faq_total} note="FAQ yang dapat ditelusuri" />
              <StatCard icon={FileBadge2} label="Sumber terverifikasi" value={stats.dokumen_terverifikasi_total} note="Dokumen aktif untuk jawaban" />
            </div>

            <div className="grid gap-6 lg:grid-cols-[1.2fr_0.8fr]">
              <article className="rounded-2xl border border-gov-line bg-white p-6 shadow-ministry">
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <p className="text-sm font-extrabold uppercase tracking-wider text-gov-blue">Asisten klasifikasi merek</p>
                    <h2 className="mt-2 text-2xl font-black text-gov-navy">Kebutuhan klasifikasi pengguna</h2>
                  </div>
                  <BarChart3 className="text-gov-gold" size={30} />
                </div>
                <div className="mt-6 grid gap-3 sm:grid-cols-2">
                  <div className="rounded-xl bg-blue-50 p-5">
                    <p className="text-4xl font-black text-gov-blue">{stats.klasifikasi_merek_total || 0}</p>
                    <p className="mt-2 text-sm font-bold text-blue-950">Analisis dengan alur klasifikasi baru</p>
                  </div>
                  <div className="rounded-xl bg-amber-50 p-5">
                    <p className="text-4xl font-black text-amber-800">{stats.klasifikasi_perlu_klarifikasi_total || 0}</p>
                    <p className="mt-2 text-sm font-bold text-amber-950">Deskripsi memerlukan informasi tambahan</p>
                  </div>
                </div>
                <p className="mt-5 text-sm leading-6 text-slate-600">Sistem membantu memilih kelas dan istilah barang/jasa. Nama dan logo tidak dinilai kemiripannya.</p>
              </article>

              <article className="rounded-2xl bg-gov-royal p-6 text-white shadow-ministry">
                <ShieldCheck className="text-gov-gold" size={34} />
                <p className="mt-5 text-sm font-bold uppercase tracking-wider text-blue-200">Kualitas arahan informasi</p>
                <p className="mt-2 text-5xl font-black">{stats.chatbot_terjawab_total}</p>
                <p className="mt-2 leading-7 text-blue-100">Pertanyaan memperoleh konteks dari dokumen yang tersedia.</p>
                <div className="mt-6 rounded-xl border border-white/15 bg-white/10 p-4">
                  <p className="text-2xl font-black text-gov-gold">{stats.chatbot_diarahkan_helpdesk_total}</p>
                  <p className="mt-1 text-sm leading-6 text-blue-100">Pertanyaan diarahkan ke Helpdesk KI karena konteks belum cukup kuat.</p>
                </div>
              </article>
            </div>

            <div className="grid gap-6 lg:grid-cols-2">
              <article className="rounded-2xl border border-gov-line bg-white p-6 shadow-ministry">
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <p className="text-sm font-extrabold uppercase tracking-wider text-gov-blue">Human oversight</p>
                    <h2 className="mt-2 text-2xl font-black text-gov-navy">Tindak lanjut konsultasi kompleks</h2>
                  </div>
                  <Clock3 className="text-gov-gold" size={30} />
                </div>
                <div className="mt-6 grid grid-cols-2 gap-3 text-center sm:grid-cols-4">
                  <OversightMetric label="Menunggu" value={stats.eskalasi?.menunggu || 0} tone="bg-amber-50 text-amber-800" />
                  <OversightMetric label="Diproses" value={stats.eskalasi?.diproses || 0} tone="bg-blue-50 text-blue-800" />
                  <OversightMetric label="Selesai" value={stats.eskalasi?.selesai || 0} tone="bg-emerald-50 text-emerald-800" />
                  <OversightMetric label="Lewat SLA" value={stats.eskalasi?.melewati_sla || 0} tone="bg-rose-50 text-rose-800" />
                </div>
                <div className="mt-3 grid grid-cols-2 gap-3 text-center">
                  <OversightMetric label="Patuh SLA" value={`${stats.eskalasi?.kepatuhan_sla_persen || 0}%`} tone="bg-emerald-50 text-emerald-800" />
                  <OversightMetric label="Rata-rata tindak lanjut" value={`${stats.eskalasi?.rata_rata_jam_tindak_lanjut || 0} jam`} tone="bg-violet-50 text-violet-800" />
                </div>
                <p className="mt-5 text-sm leading-6 text-slate-600">Status diperbarui petugas melalui dashboard admin dan tidak menggunakan rating pengguna sebagai penanda penyelesaian.</p>
              </article>

              <article className="rounded-2xl border border-gov-line bg-white p-6 shadow-ministry">
                <CheckCircle2 className="text-emerald-600" size={32} />
                <p className="mt-5 text-sm font-extrabold uppercase tracking-wider text-gov-blue">Umpan balik pengguna</p>
                <div className="mt-2 flex items-end gap-3">
                  <p className="text-5xl font-black text-gov-navy">{stats.feedback?.tingkat_membantu || 0}%</p>
                  <p className="pb-1 text-sm font-bold text-slate-500">menilai membantu</p>
                </div>
                <div className="mt-6 grid grid-cols-2 gap-3 text-sm">
                  <div className="rounded-xl bg-emerald-50 p-4"><strong className="text-2xl text-emerald-800">{stats.feedback?.membantu || 0}</strong><p className="mt-1 text-emerald-900">Membantu</p></div>
                  <div className="rounded-xl bg-rose-50 p-4"><strong className="text-2xl text-rose-800">{stats.feedback?.tidak_membantu || 0}</strong><p className="mt-1 text-rose-900">Perlu diperbaiki</p></div>
                </div>
              </article>
            </div>

            <article className="grid gap-6 rounded-2xl border border-gov-line bg-white p-6 shadow-ministry lg:grid-cols-[1fr_auto] lg:items-center">
              <div>
                <p className="text-sm font-extrabold uppercase tracking-wider text-gov-blue">Bukti uji coba pengguna</p>
                <h2 className="mt-2 text-2xl font-black text-gov-navy">Evaluasi pengalaman layanan</h2>
                <div className="mt-5 grid grid-cols-2 gap-3 sm:grid-cols-4">
                  <OversightMetric label="Responden" value={stats.uji_pengguna?.responden || 0} tone="bg-blue-50 text-blue-900" />
                  <OversightMetric label="Tugas berhasil" value={stats.uji_pengguna?.tugas_berhasil || 0} tone="bg-emerald-50 text-emerald-900" />
                  <OversightMetric label="Kemudahan / 5" value={stats.uji_pengguna?.rata_rata_kemudahan || 0} tone="bg-amber-50 text-amber-900" />
                  <OversightMetric label="Kepuasan / 5" value={stats.uji_pengguna?.rata_rata_kepuasan || 0} tone="bg-violet-50 text-violet-900" />
                </div>
                {stats.monitoring_terakhir ? <p className="mt-4 text-xs font-bold text-slate-500">Snapshot monitoring terakhir: {new Date(stats.monitoring_terakhir.dibuat_pada).toLocaleString('id-ID', { timeZone: 'Asia/Makassar' })} WITA.</p> : <p className="mt-4 text-xs font-bold text-amber-700">Snapshot monitoring belum dibuat oleh petugas.</p>}
              </div>
              <Link to="/uji-coba" className="inline-flex min-h-12 items-center justify-center rounded-xl bg-gov-royal px-5 font-black text-white">Ikuti uji coba</Link>
            </article>

            <article className="rounded-2xl border border-gov-line bg-white p-6 shadow-ministry">
              <div className="flex items-start justify-between gap-4">
                <div><p className="text-sm font-extrabold uppercase tracking-wider text-gov-blue">Monitoring layanan</p><h2 className="mt-2 text-2xl font-black text-gov-navy">Aktivitas {stats.periode_hari || period} hari terakhir</h2></div>
                <Activity className="text-gov-gold" size={30} />
              </div>
              <div className="mt-7 overflow-x-auto pb-2">
                <div className="grid h-48 items-end gap-2" style={{ gridTemplateColumns: `repeat(${(stats.tren_periode || []).length || 7}, minmax(28px, 1fr))`, minWidth: period > 7 ? `${period * 36}px` : undefined }}>
                {(stats.tren_periode || stats.tren_7_hari || []).map((item) => {
                  const total = item.chatbot + item.cek_merek
                  return (
                    <div key={item.tanggal} className="flex h-full flex-col justify-end text-center">
                      <span className="mb-2 text-xs font-black text-gov-navy">{total}</span>
                      <div className="mx-auto flex w-full max-w-12 flex-col justify-end overflow-hidden rounded-t-lg bg-slate-100" style={{ height: `${Math.max(8, (total / trendMax) * 130)}px` }} title={`${item.chatbot} chatbot, ${item.cek_merek} cek merek`}>
                        <div className="bg-gov-blue" style={{ height: `${total ? (item.chatbot / total) * 100 : 0}%` }} />
                        <div className="bg-gov-gold" style={{ height: `${total ? (item.cek_merek / total) * 100 : 0}%` }} />
                      </div>
                      <span className="mt-2 text-[10px] font-bold text-slate-500">{new Date(`${item.tanggal}T00:00:00`).toLocaleDateString('id-ID', { weekday: 'short' })}</span>
                    </div>
                  )
                })}
                </div>
              </div>
              <div className="mt-4 flex flex-wrap gap-4 text-xs font-bold text-slate-600"><span><i className="mr-2 inline-block h-3 w-3 rounded bg-gov-blue" />Chatbot</span><span><i className="mr-2 inline-block h-3 w-3 rounded bg-gov-gold" />Klasifikasi merek</span></div>
            </article>

            <div className="rounded-xl border border-blue-200 bg-blue-50 p-4 text-sm leading-6 text-blue-950">
              <strong>Cakupan data:</strong> {stats.cakupan}
              <div className="mt-2 border-t border-blue-200 pt-2">
                <strong>Data pembanding merek:</strong> {stats.mirror_merek_total || 0} baris, termasuk {stats.mirror_berita_resmi_total || 0} baris dari Berita Resmi Merek DJKI.
                {' '}{stats.mirror_etiket_total || 0} baris telah memiliki etiket dan {stats.mirror_visual_siap_total || 0} siap dibandingkan secara visual.
                {stats.sinkronisasi_merek_terakhir ? ` Sinkronisasi terakhir ${new Date(stats.sinkronisasi_merek_terakhir).toLocaleString('id-ID', { timeZone: 'Asia/Makassar' })} WITA.` : ' Belum ada sinkronisasi publikasi resmi.'}
                {stats.sinkronisasi ? ` Publikasi diproses: ${stats.sinkronisasi.berhasil} berhasil, ${stats.sinkronisasi.berjalan} berjalan, dan ${stats.sinkronisasi.gagal} gagal.` : ''}
                {stats.sinkronisasi?.cakupan_awal ? ` Rentang publikasi yang sudah masuk: ${new Date(`${stats.sinkronisasi.cakupan_awal}T00:00:00`).toLocaleDateString('id-ID')} sampai ${new Date(`${stats.sinkronisasi.cakupan_akhir}T00:00:00`).toLocaleDateString('id-ID')}.` : ''}
              </div>
            </div>
          </div>
        ) : null}
      </section>
    </>
  )
}

function exportMonitoringCsv(stats) {
  if (!stats) return
  const rows = [
    ['Tanggal', 'Chatbot', 'Klasifikasi merek'],
    ...(stats.tren_periode || []).map((item) => [item.tanggal, item.chatbot, item.cek_merek]),
    [],
    ['Indikator', 'Nilai'],
    ['Total chatbot', stats.chatbot_total],
    ['Total analisis klasifikasi merek', stats.cek_merek_total],
    ['Jawaban dinilai membantu', stats.feedback?.tingkat_membantu || 0],
    ['Kepatuhan SLA', stats.eskalasi?.kepatuhan_sla_persen || 0],
    ['Rata-rata tindak lanjut (jam)', stats.eskalasi?.rata_rata_jam_tindak_lanjut || 0],
  ]
  const csv = rows.map((row) => row.map((value) => `"${String(value ?? '').replaceAll('"', '""')}"`).join(',')).join('\r\n')
  const url = URL.createObjectURL(new Blob([`\uFEFF${csv}`], { type: 'text/csv;charset=utf-8' }))
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = `monitoring-sikap-ki-${new Date().toISOString().slice(0, 10)}.csv`
  anchor.click()
  URL.revokeObjectURL(url)
}

function OversightMetric({ label, value, tone }) {
  return <div className={`rounded-xl p-3 ${tone}`}><p className="text-3xl font-black">{value}</p><p className="mt-1 text-xs font-bold">{label}</p></div>
}

function StatCard({ icon: Icon, label, value, note }) {
  return (
    <article className="relative overflow-hidden rounded-2xl border border-gov-line bg-white p-5 shadow-soft">
      <div className="absolute right-0 top-0 h-20 w-20 rounded-bl-full bg-amber-50" />
      <Icon className="relative text-gov-blue" size={27} />
      <p className="relative mt-5 text-4xl font-black tracking-tight text-gov-navy">{value}</p>
      <h2 className="relative mt-2 font-extrabold text-gov-navy">{label}</h2>
      <p className="relative mt-1 text-sm text-slate-600">{note}</p>
    </article>
  )
}
