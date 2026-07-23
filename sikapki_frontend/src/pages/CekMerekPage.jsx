import { useEffect, useMemo, useRef, useState } from 'react'
import { CheckCircle2, CircleHelp, ExternalLink, ImagePlus, Loader2, MessageCircle, SearchCheck, ShieldAlert, X } from 'lucide-react'
import PageHeader from '../components/PageHeader.jsx'
import SpeechToTextButton from '../components/SpeechToTextButton.jsx'
import FormattedResponse from '../components/FormattedResponse.jsx'
import StatusNotice from '../components/StatusNotice.jsx'
import { cekMerek } from '../lib/api.js'
import { HELPDESK_WHATSAPP_URL, OFFICIAL_LINKS } from '../config/service.js'

const riskStyles = {
  rendah: 'border-emerald-200 bg-emerald-50 text-emerald-900',
  sedang: 'border-amber-200 bg-amber-50 text-amber-900',
  tinggi: 'border-red-200 bg-red-50 text-red-900',
}

export default function CekMerekPage() {
  const [form, setForm] = useState({ nama_merek: '', deskripsi_produk: '' })
  const [result, setResult] = useState(null)
  const [logoFile, setLogoFile] = useState(null)
  const [logoPreview, setLogoPreview] = useState('')
  const [error, setError] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [clarification, setClarification] = useState(null)
  const [selectedClasses, setSelectedClasses] = useState([])
  const [clarificationDetail, setClarificationDetail] = useState('')
  const [fieldErrors, setFieldErrors] = useState({})
  const nameInputRef = useRef(null)
  const descriptionInputRef = useRef(null)
  const feedbackRef = useRef(null)

  const loadingSteps = useMemo(() => [
    'Menganalisis deskripsi produk/jasa',
    'Mengusulkan kelas Nice',
    'Membandingkan nama dengan data merek',
    'Membandingkan visual etiket bila logo diunggah',
    'Menyusun saran naratif',
  ], [])

  useEffect(() => {
    if (!logoFile) {
      setLogoPreview('')
      return undefined
    }
    const previewUrl = URL.createObjectURL(logoFile)
    setLogoPreview(previewUrl)
    return () => URL.revokeObjectURL(previewUrl)
  }, [logoFile])

  useEffect(() => {
    if ((result || clarification || error) && !isLoading) feedbackRef.current?.focus()
  }, [result, clarification, error, isLoading])

  function handleLogoChange(event) {
    const file = event.target.files?.[0]
    if (!file) return
    if (!['image/png', 'image/jpeg'].includes(file.type)) {
      setError('Logo harus berformat PNG atau JPEG.')
      event.target.value = ''
      return
    }
    if (file.size > 5 * 1024 * 1024) {
      setError('Ukuran logo maksimal 5 MB.')
      event.target.value = ''
      return
    }
    setError('')
    setLogoFile(file)
  }

  async function runCheck({ classes = [], description = form.deskripsi_produk } = {}) {
    setError('')
    setResult(null)
    setIsLoading(true)
    try {
      const data = await cekMerek({
        ...form,
        deskripsi_produk: description,
        kelas_nice_dipilih: classes,
      }, logoFile)
      if (data.perlu_klarifikasi) {
        setClarification(data)
        setSelectedClasses([])
      } else {
        setClarification(null)
        setSelectedClasses([])
        setResult(data)
      }
    } catch (err) {
      setError(err.message)
    } finally {
      setIsLoading(false)
    }
  }

  async function handleSubmit(event) {
    event.preventDefault()
    const errors = {}
    if (!form.nama_merek.trim()) errors.nama_merek = 'Nama merek wajib diisi.'
    else if (form.nama_merek.trim().length < 2) errors.nama_merek = 'Nama merek minimal 2 karakter.'
    if (!form.deskripsi_produk.trim()) errors.deskripsi_produk = 'Deskripsi produk atau jasa wajib diisi.'
    else if (form.deskripsi_produk.trim().length < 10) errors.deskripsi_produk = 'Deskripsi perlu minimal 10 karakter agar kelas dapat dianalisis.'
    setFieldErrors(errors)
    if (Object.keys(errors).length) {
      setError('Periksa kembali kolom yang ditandai pada formulir.')
      window.requestAnimationFrame(() => (errors.nama_merek ? nameInputRef : descriptionInputRef).current?.focus())
      return
    }
    setClarification(null)
    setSelectedClasses([])
    setClarificationDetail('')
    await runCheck()
  }

  function toggleClass(classNumber) {
    setError('')
    setSelectedClasses((current) => {
      if (current.includes(classNumber)) return current.filter((item) => item !== classNumber)
      if (current.length >= 2) {
        setError('Pilih maksimal dua kelas Nice yang paling sesuai.')
        return current
      }
      return [...current, classNumber]
    })
  }

  async function continueWithSelectedClasses() {
    if (!selectedClasses.length) {
      setError('Pilih minimal satu kelas Nice sebelum melanjutkan.')
      return
    }
    await runCheck({ classes: selectedClasses })
  }

  async function analyzeAdditionalDetail() {
    const detail = clarificationDetail.trim()
    if (!detail) {
      setError('Isi keterangan tambahan agar sistem dapat menganalisis ulang kelas.')
      return
    }
    const description = `${form.deskripsi_produk.trim()}\nKeterangan tambahan: ${detail}`
    setForm((current) => ({ ...current, deskripsi_produk: description }))
    setClarification(null)
    setClarificationDetail('')
    await runCheck({ description })
  }

  return (
    <>
      <PageHeader
        eyebrow="Asisten Penelusuran Awal Merek"
        title="Kenali indikasi kemiripan sebelum mengajukan"
        description="Bandingkan unsur nama pada data publikasi resmi DJKI yang tersedia, lihat kelas Nice, dan tinjau aspek label. Hasil bersifat informatif dan bukan keputusan pemeriksaan."
      />
      <section className="mx-auto grid max-w-6xl gap-6 px-4 py-8 lg:grid-cols-[0.95fr_1.05fr]">
        <form onSubmit={handleSubmit} noValidate className="rounded-lg border border-gov-line bg-white p-5 shadow-soft" aria-describedby={Object.keys(fieldErrors).length ? 'form-error-summary' : undefined}>
          {Object.keys(fieldErrors).length ? <p id="form-error-summary" className="mb-4 rounded-lg border border-red-200 bg-red-50 p-3 text-sm font-bold text-red-900" role="alert">Ada {Object.keys(fieldErrors).length} kolom yang perlu diperbaiki.</p> : null}
          <div className="space-y-5">
            <div>
              <label htmlFor="nama_merek" className="block text-sm font-bold text-gov-navy">Nama merek</label>
              <input
                ref={nameInputRef}
                id="nama_merek"
                value={form.nama_merek}
                onChange={(event) => { setForm({ ...form, nama_merek: event.target.value }); setFieldErrors((current) => ({ ...current, nama_merek: '' })) }}
                className={`mt-2 min-h-12 w-full rounded-md border px-3 outline-none focus:border-gov-teal focus:ring-2 focus:ring-gov-mint ${fieldErrors.nama_merek ? 'border-red-500' : 'border-gov-line'}`}
                placeholder="Contoh: Kopi Kita"
                aria-invalid={Boolean(fieldErrors.nama_merek)}
                aria-describedby={fieldErrors.nama_merek ? 'nama-merek-error' : undefined}
              />
              {fieldErrors.nama_merek ? <p id="nama-merek-error" className="mt-2 text-sm font-semibold text-red-700">{fieldErrors.nama_merek}</p> : null}
            </div>
            <div>
              <label htmlFor="deskripsi_produk" className="block text-sm font-bold text-gov-navy">Deskripsi produk/jasa</label>
              <textarea
                ref={descriptionInputRef}
                id="deskripsi_produk"
                value={form.deskripsi_produk}
                onChange={(event) => { setForm({ ...form, deskripsi_produk: event.target.value }); setFieldErrors((current) => ({ ...current, deskripsi_produk: '' })) }}
                className={`mt-2 min-h-40 w-full rounded-md border px-3 py-3 outline-none focus:border-gov-teal focus:ring-2 focus:ring-gov-mint ${fieldErrors.deskripsi_produk ? 'border-red-500' : 'border-gov-line'}`}
                placeholder="Contoh: produk kopi bubuk dan minuman kopi siap saji"
                aria-invalid={Boolean(fieldErrors.deskripsi_produk)}
                aria-describedby={fieldErrors.deskripsi_produk ? 'deskripsi-produk-error deskripsi-produk-help' : 'deskripsi-produk-help'}
              />
              {fieldErrors.deskripsi_produk ? <p id="deskripsi-produk-error" className="mt-2 text-sm font-semibold text-red-700">{fieldErrors.deskripsi_produk}</p> : null}
              <div className="mt-2 flex items-start gap-3">
                <SpeechToTextButton
                  value={form.deskripsi_produk}
                  onChange={(value) => setForm({ ...form, deskripsi_produk: value })}
                  disabled={isLoading}
                />
                <p id="deskripsi-produk-help" className="pt-2 text-xs leading-5 text-slate-500">Ucapkan deskripsi produk atau jasa dalam Bahasa Indonesia.</p>
              </div>
            </div>
            <div>
              <div className="flex items-center justify-between gap-3">
                <label htmlFor="logo_merek" className="block text-sm font-bold text-gov-navy">Logo/etiket merek <span className="font-normal text-slate-500">(opsional)</span></label>
                <span className="text-xs text-slate-500">PNG/JPEG, maks. 5 MB</span>
              </div>
              {logoPreview ? (
                <div className="mt-2 flex items-center gap-4 rounded-xl border border-gov-line bg-gov-paper p-3">
                  <img src={logoPreview} alt="Pratinjau logo yang akan dianalisis" className="h-24 w-24 rounded-lg border border-white bg-white object-contain p-2 shadow-sm" />
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-bold text-gov-navy">{logoFile.name}</p>
                    <p className="mt-1 text-xs leading-5 text-slate-600">Diproses sementara dan tidak disimpan sebagai file pengguna.</p>
                  </div>
                  <button type="button" onClick={() => setLogoFile(null)} className="rounded-full border border-gov-line bg-white p-2 text-slate-600 hover:text-red-600" aria-label="Hapus logo"><X size={18} /></button>
                </div>
              ) : (
                <label htmlFor="logo_merek" className="mt-2 flex cursor-pointer items-center gap-4 rounded-xl border-2 border-dashed border-gov-line bg-gov-paper p-4 transition hover:border-gov-teal hover:bg-teal-50">
                  <span className="flex h-12 w-12 items-center justify-center rounded-xl bg-white text-gov-teal shadow-sm"><ImagePlus size={24} /></span>
                  <span><span className="block text-sm font-bold text-gov-navy">Pilih file logo</span><span className="mt-1 block text-xs text-slate-600">Visual dibandingkan dengan etiket referensi yang tersedia di mirror PDKI.</span></span>
                </label>
              )}
              <input id="logo_merek" type="file" accept="image/png,image/jpeg" onChange={handleLogoChange} className="sr-only" />
            </div>
            <button
              type="submit"
              disabled={isLoading}
              className="inline-flex min-h-14 w-full items-center justify-center gap-3 rounded-lg bg-gov-teal px-5 text-base font-bold text-white transition hover:bg-teal-700 disabled:cursor-not-allowed disabled:bg-slate-400"
            >
              {isLoading ? <Loader2 className="h-5 w-5 animate-spin" aria-hidden="true" /> : <SearchCheck size={21} aria-hidden="true" />}
              {isLoading ? 'Memproses penelusuran' : 'Analisis Kelas & Telusuri Merek'}
            </button>
          </div>
        </form>

        <div ref={feedbackRef} tabIndex="-1" className="space-y-4 focus:outline-none" aria-label="Status dan hasil penelusuran">
          <div className="sr-only" aria-live="polite" aria-atomic="true">
            {isLoading ? 'Penelusuran sedang diproses.' : error ? `Pengecekan gagal. ${error}` : clarification ? 'Kelas Nice perlu dikonfirmasi.' : result ? 'Hasil penelusuran merek telah tersedia.' : ''}
          </div>
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

          {clarification && !isLoading ? (
            <ClassClarification
              data={clarification}
              selectedClasses={selectedClasses}
              detail={clarificationDetail}
              onToggleClass={toggleClass}
              onDetailChange={setClarificationDetail}
              onContinue={continueWithSelectedClasses}
              onAnalyzeDetail={analyzeAdditionalDetail}
            />
          ) : null}

          {!result && !isLoading && !clarification ? (
            <StatusNotice title="Hasil akan tampil di sini">
              Setelah formulir dikirim, sistem menampilkan kelas Nice, indikator kemiripan, data pembanding, dan arahan peninjauan label.
            </StatusNotice>
          ) : null}

          {result ? <CekMerekResult result={result} /> : null}
        </div>
      </section>
    </>
  )
}

function ClassClarification({
  data, selectedClasses, detail, onToggleClass, onDetailChange, onContinue, onAnalyzeDetail,
}) {
  return (
    <div className="rounded-2xl border border-amber-200 bg-amber-50 p-5 shadow-soft">
      <div className="flex items-start gap-3">
        <CircleHelp className="mt-0.5 shrink-0 text-amber-700" size={24} />
        <div>
          <p className="font-black text-amber-950">Kelas Nice perlu dikonfirmasi</p>
          <p className="mt-1 text-sm leading-6 text-amber-900">{data.pertanyaan_klarifikasi}</p>
        </div>
      </div>

      <div className="mt-4 space-y-3">
        {(data.opsi_kelas || []).map((option) => {
          const selected = selectedClasses.includes(option.kelas)
          return (
            <button
              type="button"
              key={option.kelas}
              onClick={() => onToggleClass(option.kelas)}
              className={`w-full rounded-xl border p-4 text-left transition ${selected ? 'border-gov-teal bg-white ring-2 ring-gov-mint' : 'border-amber-200 bg-white/70 hover:border-amber-400'}`}
            >
              <div className="flex items-center justify-between gap-3">
                <span className="flex items-center gap-2 font-black text-gov-navy">
                  {selected ? <CheckCircle2 className="text-gov-teal" size={20} /> : null}
                  Kelas {option.kelas}
                </span>
                <span className="rounded-full bg-gov-paper px-3 py-1 text-xs font-bold text-slate-600">Keyakinan {Math.round(Number(option.keyakinan || 0) * 100)}%</span>
              </div>
              <p className="mt-2 text-sm font-semibold leading-6 text-slate-800">{option.alasan}</p>
              <p className="mt-1 text-xs leading-5 text-slate-600">{option.deskripsi_kelas}</p>
              {(option.istilah_resmi || []).length > 0 ? (
                <div className="mt-3 rounded-lg border border-blue-100 bg-blue-50/70 p-3">
                  <p className="text-xs font-black uppercase tracking-wide text-gov-blue">Istilah resmi terdekat</p>
                  <ul className="mt-2 space-y-1 text-xs leading-5 text-slate-700">
                    {option.istilah_resmi.slice(0, 3).map((term) => (
                      <li key={`${term.basic_number}-${term.istilah}`}>
                        <span className="font-bold">{term.istilah}</span> <span className="text-slate-500">({term.basic_number}, cocok {Math.round(term.skor)}%)</span>
                      </li>
                    ))}
                  </ul>
                </div>
              ) : null}
              {option.sumber ? <p className="mt-3 text-xs font-bold text-gov-blue">Sumber: {option.sumber}</p> : null}
            </button>
          )
        })}
        {!(data.opsi_kelas || []).length ? (
          <div className="rounded-xl border border-amber-300 bg-white p-4 text-sm leading-6 text-amber-950">
            Belum ada kandidat kelas yang cukup kuat untuk dipilih. Tambahkan fungsi, bentuk, pengguna, atau tujuan penggunaan produk pada kolom di bawah.
          </div>
        ) : null}
      </div>

      {(data.opsi_kelas || []).length ? (
        <button type="button" onClick={onContinue} className="mt-4 inline-flex min-h-12 w-full items-center justify-center gap-2 rounded-lg bg-gov-teal px-4 font-bold text-white hover:bg-teal-700">
          <SearchCheck size={18} /> Lanjutkan dengan kelas dipilih
        </button>
      ) : null}

      <div className="my-5 flex items-center gap-3 text-xs font-bold uppercase tracking-wider text-amber-800">
        <span className="h-px flex-1 bg-amber-200" /> atau tambahkan informasi <span className="h-px flex-1 bg-amber-200" />
      </div>
      <textarea
        value={detail}
        onChange={(event) => onDetailChange(event.target.value)}
        className="min-h-24 w-full rounded-lg border border-amber-200 bg-white px-3 py-3 text-sm outline-none focus:border-gov-teal focus:ring-2 focus:ring-gov-mint"
        placeholder="Contoh: digunakan sebagai bahan baku cat industri; atau dikemas sebagai suplemen mineral untuk dikonsumsi."
      />
      <button type="button" onClick={onAnalyzeDetail} className="mt-3 inline-flex min-h-11 w-full items-center justify-center rounded-lg border border-gov-teal bg-white px-4 text-sm font-bold text-gov-teal hover:bg-teal-50">
        Analisis ulang dengan keterangan tambahan
      </button>
      <p className="mt-3 text-xs leading-5 text-amber-900">Pilihan kelas merupakan bantuan awal. Pengguna tetap perlu memeriksa daftar barang/jasa dan klasifikasi resmi DJKI sebelum mengajukan.</p>
    </div>
  )
}

function CekMerekResult({ result }) {
  const risk = result.skor_risiko || 'rendah'
  const similarity = Number(result.persentase_kemiripan || 0)
  const gaugeColor = risk === 'tinggi' ? '#e11d48' : risk === 'sedang' ? '#f59e0b' : '#059669'
  const visualSimilarity = result.persentase_kemiripan_visual
  return (
    <div className="space-y-4">
      <div className="grid gap-4 md:grid-cols-[0.85fr_1.15fr]">
        <div className="rounded-2xl border border-gov-line bg-white p-5 shadow-soft">
          <p className="text-sm font-bold uppercase tracking-wide text-gov-blue">
            {result.sumber_klasifikasi === 'dipilih_pengguna' ? 'Kelas Nice dikonfirmasi pengguna' : 'Kelas Nice hasil analisis'}
          </p>
          <div className="mt-4 flex flex-wrap gap-2">
            {(result.kelas_nice_terdeteksi || []).map((kelas) => (
              <span key={kelas} className="rounded-xl bg-blue-50 px-4 py-2 text-lg font-black text-gov-royal">Kelas {kelas}</span>
            ))}
          </div>
          <p className="mt-3 text-xs leading-5 text-slate-600">
            {result.sumber_klasifikasi === 'dipilih_pengguna'
              ? 'Pengecekan menggunakan kelas yang Anda pilih pada tahap klarifikasi.'
              : 'Sistem melanjutkan otomatis karena satu kelas memiliki keyakinan yang cukup kuat.'}
          </p>
          {(result.bukti_klasifikasi || []).map((evidence) => (
            <div key={evidence.kelas} className="mt-4 rounded-xl border border-blue-100 bg-blue-50 p-3 text-xs">
              <p className="font-black text-gov-blue">Dasar Kelas {evidence.kelas}: {evidence.sumber}</p>
              {(evidence.istilah_resmi || []).slice(0, 3).map((term) => <p key={term.basic_number} className="mt-1 text-slate-700">{term.istilah} <span className="text-slate-500">({term.basic_number})</span></p>)}
            </div>
          ))}
          <div className="mt-5 flex flex-wrap gap-4 text-sm font-bold text-gov-blue">
            {(result.kelas_nice_terdeteksi || []).map((kelas) => (
              <a key={kelas} href={`https://skm.dgip.go.id/index.php/skm/detailkelas/${kelas}`} target="_blank" rel="noreferrer" className="inline-flex items-center gap-2 hover:underline">
                Verifikasi Kelas {kelas} di SKM DJKI <ExternalLink size={15} />
              </a>
            ))}
            <a href={OFFICIAL_LINKS.niceWipo} target="_blank" rel="noreferrer" className="inline-flex items-center gap-2 hover:underline">Sumber WIPO <ExternalLink size={15} /></a>
          </div>
        </div>

        <div className={`rounded-2xl border p-5 ${riskStyles[risk] || riskStyles.rendah}`}>
          <div className="flex items-center gap-5">
            <div className="relative flex h-28 w-28 shrink-0 items-center justify-center rounded-full" style={{ background: `conic-gradient(${gaugeColor} ${similarity * 3.6}deg, rgba(148,163,184,.22) 0deg)` }}>
              <div className="flex h-20 w-20 flex-col items-center justify-center rounded-full bg-white shadow-inner">
                <span className="text-3xl font-black text-gov-navy">{similarity}%</span>
                <span className="text-[10px] font-bold uppercase tracking-wide text-slate-500">indikator</span>
              </div>
            </div>
            <div>
              <p className="text-xs font-bold uppercase tracking-wider">Indikasi kemiripan tertinggi</p>
              <p className="mt-1 text-2xl font-black capitalize">{risk}</p>
              <p className="mt-2 text-xs leading-5 opacity-80">Bukan probabilitas diterima atau ditolak. Angka menunjukkan skor gabungan tertinggi; tanpa referensi visual, skor berasal dari nama.</p>
            </div>
          </div>
        </div>
      </div>

      {result.cakupan_data ? (
        <div className="rounded-2xl border border-gov-line bg-white p-5 shadow-soft">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <p className="font-black text-gov-navy">Cakupan data pada kelas yang diperiksa</p>
              <p className="mt-1 text-sm leading-6 text-slate-600">Transparansi ini menunjukkan seberapa banyak pembanding yang benar-benar tersedia pada portal.</p>
            </div>
            <span className="rounded-full bg-blue-50 px-3 py-1 text-xs font-black text-gov-blue">Kelas {(result.cakupan_data.kelas || []).join(', ')}</span>
          </div>
          <div className="mt-4 grid gap-3 sm:grid-cols-3">
            <DataMetric label="Data pembanding" value={formatNumber(result.cakupan_data.total_pembanding_kelas)} />
            <DataMetric label="Etiket tersedia" value={formatNumber(result.cakupan_data.etiket_tersedia)} />
            <DataMetric label="Cakupan analisis visual" value={`${result.cakupan_data.cakupan_visual_persen || 0}%`} />
          </div>
          <p className="mt-4 text-xs leading-5 text-slate-500">
            Rentang publikasi: {formatDate(result.cakupan_data.publikasi_awal)}–{formatDate(result.cakupan_data.publikasi_akhir)}. Data terakhir diproses {formatDateTime(result.cakupan_data.sinkron_terakhir)}.
          </p>
          <details className="mt-4 rounded-xl bg-gov-paper p-4">
            <summary className="cursor-pointer text-sm font-black text-gov-blue">Bagaimana indikator dihitung?</summary>
            <ul className="mt-3 space-y-2 text-xs leading-5 text-slate-600">
              {(result.metodologi || []).map((item) => <li key={item}>• {item}</li>)}
            </ul>
          </details>
        </div>
      ) : null}

      {result.logo_dianalisis ? (
        result.referensi_visual_dibandingkan > 0 ? (
          <div className="rounded-2xl border border-blue-200 bg-blue-50 p-5">
            <div className="flex items-center justify-between gap-5">
              <div>
                <p className="text-sm font-black uppercase tracking-wide text-gov-blue">Kemiripan visual tertinggi</p>
                <p className="mt-2 text-sm leading-6 text-slate-700">Logo dibandingkan dengan {result.referensi_visual_dibandingkan} etiket referensi pada kelas terkait.</p>
              </div>
              <span className="text-4xl font-black text-gov-royal">{visualSimilarity ?? 0}%</span>
            </div>
          </div>
        ) : (
          <StatusNotice tone="warning" title="Logo berhasil dianalisis, referensi visual belum tersedia">
            Mirror saat ini belum memiliki embedding etiket PDKI pada kelas terkait. Admin perlu menambahkan gambar etiket dari sumber resmi; penilaian ini sementara memakai kemiripan nama saja.
          </StatusNotice>
        )
      ) : null}

      <div className="rounded-2xl border border-gov-line bg-white p-5 shadow-soft">
        <div className="flex items-start gap-3">
          <ShieldAlert className="mt-0.5 shrink-0 text-gov-blue" size={23} />
          <div>
            <p className="font-black text-gov-navy">Kandidat pembanding pada data yang tersedia</p>
            <p className="mt-1 text-sm leading-6 text-slate-600">Hanya kandidat dengan kemiripan kuat pada kelas Nice yang dipilih yang ditampilkan. Lakukan penelusuran ulang pada PDKI resmi sebelum mengajukan.</p>
          </div>
        </div>
        {(result.merek_mirip || []).length ? (
          <>
          <div className="mt-4 grid gap-3 md:hidden" aria-label="Kandidat pembanding merek">
            {result.merek_mirip.map((item) => (
              <article key={`card-${item.nama}-${item.kelas}-${item.skor_kemiripan}`} className="rounded-xl border border-gov-line bg-gov-paper p-4">
                <div className="flex items-start gap-3">
                  {item.label_merek_url ? <img src={item.label_merek_url} alt={`Etiket ${item.nama}`} className="h-16 w-16 shrink-0 rounded-lg border border-gov-line bg-white object-contain p-1" loading="lazy" /> : null}
                  <div className="min-w-0">
                    <h3 className="break-words font-black text-gov-navy">{item.nama}</h3>
                    {item.nomor_permohonan ? <p className="mt-1 text-xs text-slate-600">Nomor permohonan: {item.nomor_permohonan}</p> : null}
                    {item.sumber_data_url ? <a href={item.sumber_data_url} target="_blank" rel="noreferrer" className="mt-2 inline-flex min-h-10 items-center gap-1 text-xs font-bold text-gov-blue underline">Sumber DJKI <ExternalLink size={12} aria-hidden="true" /></a> : null}
                  </div>
                </div>
                <dl className="mt-3 grid grid-cols-2 gap-2 text-sm">
                  <MobileMetric label="Kelas" value={item.kelas} />
                  <MobileMetric label="Status" value={item.status} />
                  <MobileMetric label="Kemiripan nama" value={`${item.skor_kemiripan}%`} />
                  <MobileMetric label="Kemiripan visual" value={item.skor_visual == null ? 'Tidak tersedia' : `${item.skor_visual}%`} />
                  <div className="col-span-2"><MobileMetric label="Skor gabungan" value={`${item.skor_gabungan ?? item.skor_kemiripan}%`} emphasized /></div>
                </dl>
                {(item.alasan_kemiripan || []).length ? <ul className="mt-3 list-disc space-y-1 pl-5 text-xs leading-5 text-slate-700">{item.alasan_kemiripan.map((reason) => <li key={reason}>{reason}</li>)}</ul> : null}
              </article>
            ))}
          </div>
          <div className="mobile-scroll mt-3 hidden overflow-x-auto md:block">
            <table className="w-full min-w-[560px] border-collapse text-left text-sm">
              <caption className="sr-only">Daftar kandidat merek pembanding beserta kelas, status, dan skor kemiripan</caption>
              <thead className="bg-gov-paper text-gov-navy">
                <tr>
                  <th scope="col" className="border-b border-gov-line px-3 py-3">Nama merek</th>
                  <th scope="col" className="border-b border-gov-line px-3 py-3">Kelas</th>
                  <th scope="col" className="border-b border-gov-line px-3 py-3">Status</th>
                  <th scope="col" className="border-b border-gov-line px-3 py-3">Kemiripan nama</th>
                  <th scope="col" className="border-b border-gov-line px-3 py-3">Kemiripan visual</th>
                  <th scope="col" className="border-b border-gov-line px-3 py-3">Skor gabungan</th>
                </tr>
              </thead>
              <tbody>
                {result.merek_mirip.map((item) => (
                  <tr key={`${item.nama}-${item.kelas}-${item.skor_kemiripan}`}>
                    <td className="border-b border-gov-line px-3 py-3 font-semibold">
                      <div className="flex items-start gap-3">
                        {item.label_merek_url ? <img src={item.label_merek_url} alt={`Etiket ${item.nama}`} className="h-14 w-14 shrink-0 rounded-lg border border-gov-line bg-white object-contain p-1" loading="lazy" /> : null}
                        <div>
                          <span className="block">{item.nama}</span>
                          {item.nomor_permohonan ? <span className="mt-1 block text-xs font-normal text-slate-500">{item.nomor_permohonan}</span> : null}
                          {item.sumber_data_url ? <a href={item.sumber_data_url} target="_blank" rel="noreferrer" className="mt-1 inline-flex items-center gap-1 text-xs font-bold text-gov-blue hover:underline">Sumber DJKI <ExternalLink size={12} /></a> : null}
                          {(item.alasan_kemiripan || []).length ? (
                            <ul className="mt-2 space-y-1 text-xs font-normal leading-5 text-slate-600">
                              {item.alasan_kemiripan.map((reason) => <li key={reason}>• {reason}</li>)}
                            </ul>
                          ) : null}
                        </div>
                      </div>
                    </td>
                    <td className="border-b border-gov-line px-3 py-3">{item.kelas}</td>
                    <td className="border-b border-gov-line px-3 py-3">{item.status}</td>
                    <td className="border-b border-gov-line px-3 py-3 font-bold">{item.skor_kemiripan}%</td>
                    <td className="border-b border-gov-line px-3 py-3 font-bold">{item.skor_visual == null ? '—' : `${item.skor_visual}%`}</td>
                    <td className="border-b border-gov-line px-3 py-3 font-black text-gov-blue">{item.skor_gabungan ?? item.skor_kemiripan}%</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          </>
        ) : (
          <p className="mt-4 text-sm leading-6 text-slate-700">Belum ditemukan kandidat di atas ambang penelusuran pada data pembanding portal.</p>
        )}
      </div>

      <div className="rounded-2xl border border-gov-line bg-white p-5 shadow-soft">
        <p className="font-black text-gov-navy">Arahan peninjauan label</p>
        <FormattedResponse text={result.saran_naratif} className="mt-3 text-sm text-slate-700" />
      </div>

      <a href={HELPDESK_WHATSAPP_URL} target="_blank" rel="noreferrer" className="flex items-center justify-between gap-4 rounded-2xl bg-gov-royal p-5 text-white shadow-ministry transition hover:bg-blue-900">
        <div>
          <p className="font-black">Perlu penjelasan hasil?</p>
          <p className="mt-1 text-sm text-blue-100">Hubungi Helpdesk KI Kantor Wilayah Kementerian Hukum Nusa Tenggara Barat.</p>
        </div>
        <span className="flex h-12 w-12 shrink-0 items-center justify-center rounded-full bg-[#128c4a]"><MessageCircle size={24} /></span>
      </a>

      <StatusNotice tone="warning" title="Disclaimer penting">
        {result.disclaimer}
      </StatusNotice>
    </div>
  )
}

function DataMetric({ label, value }) {
  return <div className="rounded-xl bg-gov-paper p-4"><p className="text-xs font-bold uppercase tracking-wide text-slate-500">{label}</p><p className="mt-1 text-2xl font-black text-gov-navy">{value}</p></div>
}

function MobileMetric({ label, value, emphasized = false }) {
  return <div className={`rounded-lg bg-white p-2 ${emphasized ? 'border border-gov-blue' : ''}`}><dt className="text-xs font-bold text-slate-600">{label}</dt><dd className={`mt-1 ${emphasized ? 'font-black text-gov-blue' : 'font-semibold text-gov-navy'}`}>{value || 'Tidak tersedia'}</dd></div>
}

function formatNumber(value) {
  return Number(value || 0).toLocaleString('id-ID')
}

function formatDate(value) {
  if (!value) return 'belum tersedia'
  return new Date(`${value}T00:00:00`).toLocaleDateString('id-ID', { year: 'numeric', month: 'short', day: 'numeric' })
}

function formatDateTime(value) {
  if (!value) return 'belum tersedia'
  return new Date(value).toLocaleString('id-ID', { timeZone: 'Asia/Makassar', dateStyle: 'medium', timeStyle: 'short' }) + ' WITA'
}
