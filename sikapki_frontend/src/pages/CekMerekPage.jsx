import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  BookOpenCheck, CircleHelp, ExternalLink, ImagePlus, Info,
  Loader2, MessageCircle, SearchCheck, ShieldAlert, ShieldCheck, X,
} from 'lucide-react'
import PageHeader from '../components/PageHeader.jsx'
import SpeechToTextButton from '../components/SpeechToTextButton.jsx'
import StatusNotice from '../components/StatusNotice.jsx'
import {
  analisisKlasifikasiMerek, cekKemiripanMerek, eskalasiKelasMerek, getFiturMerek,
} from '../lib/api.js'
import { HELPDESK_WHATSAPP_URL, OFFICIAL_LINKS } from '../config/service.js'

const MAX_LOGO_SIZE = 5 * 1024 * 1024

export default function CekMerekPage() {
  const [mode, setMode] = useState('classification')
  const [similarityEnabled, setSimilarityEnabled] = useState(false)
  const [form, setForm] = useState({ nama_merek: '', deskripsi_produk: '' })
  const [logoFile, setLogoFile] = useState(null)
  const [logoPreview, setLogoPreview] = useState('')
  const [additionalDetail, setAdditionalDetail] = useState('')
  const [result, setResult] = useState(null)
  const [error, setError] = useState('')
  const [fieldErrors, setFieldErrors] = useState({})
  const [isLoading, setIsLoading] = useState(false)
  const [isEscalating, setIsEscalating] = useState(false)
  const [escalation, setEscalation] = useState(null)
  const [emailPengguna, setEmailPengguna] = useState('')
  const nameInputRef = useRef(null)
  const descriptionInputRef = useRef(null)
  const feedbackRef = useRef(null)

  useEffect(() => {
    let mounted = true
    getFiturMerek()
      .then((data) => {
        if (mounted) setSimilarityEnabled(Boolean(data.ai_cek_merek_aktif))
      })
      .catch(() => {
        if (mounted) setSimilarityEnabled(false)
      })
    return () => { mounted = false }
  }, [])

  useEffect(() => {
    if (!logoFile) {
      setLogoPreview('')
      return undefined
    }
    const url = URL.createObjectURL(logoFile)
    setLogoPreview(url)
    return () => URL.revokeObjectURL(url)
  }, [logoFile])

  useEffect(() => {
    if ((result || error) && !isLoading) feedbackRef.current?.focus()
  }, [result, error, isLoading])

  function handleLogoChange(event) {
    const file = event.target.files?.[0]
    if (!file) return
    if (!['image/png', 'image/jpeg'].includes(file.type)) {
      setError('Logo harus berformat PNG atau JPEG.')
      event.target.value = ''
      return
    }
    if (file.size > MAX_LOGO_SIZE) {
      setError('Ukuran logo maksimal 5 MB.')
      event.target.value = ''
      return
    }
    setError('')
    setLogoFile(file)
  }

  async function runAnalysis(description) {
    setError('')
    setResult(null)
    setEscalation(null)
    setIsLoading(true)
    try {
      const payload = {
        nama_merek: form.nama_merek.trim(),
        deskripsi_produk: description.trim(),
      }
      const data = mode === 'similarity'
        ? await cekKemiripanMerek(payload, logoFile)
        : await analisisKlasifikasiMerek(payload)
      setResult(data)
    } catch (err) {
      setError(err.message)
    } finally {
      setIsLoading(false)
    }
  }

  async function handleEscalateClass() {
    if (!result || isEscalating) return
    setError('')
    setIsEscalating(true)
    try {
      const response = await eskalasiKelasMerek({
        nama_merek: form.nama_merek.trim(),
        deskripsi_produk: form.deskripsi_produk.trim(),
        email_pengguna: emailPengguna.trim(),
        rekomendasi_kelas: result.rekomendasi_kelas || [],
      })
      setEscalation(response)
    } catch (err) {
      setError(err.message)
    } finally {
      setIsEscalating(false)
    }
  }

  function changeMode(nextMode) {
    setMode(nextMode)
    setResult(null)
    setError('')
    setAdditionalDetail('')
  }

  async function handleSubmit(event) {
    event.preventDefault()
    const errors = {}
    if (!form.nama_merek.trim()) errors.nama_merek = 'Nama merek wajib diisi.'
    else if (form.nama_merek.trim().length < 2) errors.nama_merek = 'Nama merek minimal 2 karakter.'
    if (!form.deskripsi_produk.trim()) errors.deskripsi_produk = 'Deskripsi produk atau jasa wajib diisi.'
    else if (form.deskripsi_produk.trim().length < 10) {
      errors.deskripsi_produk = 'Jelaskan produk atau jasa minimal 10 karakter.'
    }
    setFieldErrors(errors)
    if (Object.keys(errors).length) {
      setError('Periksa kembali kolom yang ditandai.')
      window.requestAnimationFrame(() => (
        errors.nama_merek ? nameInputRef : descriptionInputRef
      ).current?.focus())
      return
    }
    setAdditionalDetail('')
    await runAnalysis(form.deskripsi_produk)
  }

  async function handleClarification() {
    if (!additionalDetail.trim()) {
      setError('Isi keterangan tambahan agar kelas dapat dianalisis lebih tepat.')
      return
    }
    const combined = `${form.deskripsi_produk.trim()}\nKeterangan tambahan: ${additionalDetail.trim()}`
    setForm((current) => ({ ...current, deskripsi_produk: combined }))
    setAdditionalDetail('')
    await runAnalysis(combined)
  }

  return (
    <>
      <PageHeader
        eyebrow="Asisten Penelusuran Awal Merek"
        title={mode === 'similarity' ? 'Cek indikator kemiripan pada data pembanding' : 'Temukan kelas barang atau jasa yang paling relevan'}
        description={mode === 'similarity'
          ? 'Fitur opsional ini membandingkan nama dan logo dengan data lokal yang tersedia. Hasil bukan keputusan pemeriksa dan wajib diverifikasi melalui PDKI.'
          : 'AI membantu menganalisis deskripsi produk atau jasa untuk merekomendasikan kelas Nice dan istilah barang/jasa resmi. Nama dan logo tidak dinilai kemiripannya.'}
      />

      <section className="mx-auto max-w-6xl px-4 py-8">
        {similarityEnabled ? (
          <div className="mb-6 grid gap-2 rounded-2xl border border-gov-line bg-white p-2 shadow-soft sm:grid-cols-2" role="tablist" aria-label="Pilih fungsi asisten merek">
            <button type="button" role="tab" aria-selected={mode === 'classification'} onClick={() => changeMode('classification')} className={`min-h-12 rounded-xl px-4 text-sm font-black transition ${mode === 'classification' ? 'bg-gov-royal text-white' : 'text-slate-700 hover:bg-gov-paper'}`}>
              Rekomendasi Kelas
            </button>
            <button type="button" role="tab" aria-selected={mode === 'similarity'} onClick={() => changeMode('similarity')} className={`min-h-12 rounded-xl px-4 text-sm font-black transition ${mode === 'similarity' ? 'bg-gov-royal text-white' : 'text-slate-700 hover:bg-gov-paper'}`}>
              AI Cek Merek
            </button>
          </div>
        ) : null}
        <div className="mb-6 grid gap-3 md:grid-cols-3">
          <FlowStep number="1" title="Jelaskan usaha" text="Isi nama merek, logo opsional, dan uraian produk atau jasa." />
          <FlowStep number="2" title={mode === 'similarity' ? 'Tinjau indikator' : 'Tinjau rekomendasi'} text={mode === 'similarity' ? 'Lihat kandidat pembanding dari data portal yang tersedia.' : 'Lihat beberapa kelas, istilah resmi, dan alasan relevansinya.'} />
          <FlowStep number="3" title="Periksa secara resmi" text={mode === 'similarity' ? 'Ulangi penelusuran nama dan gambar pada PDKI.' : 'Konfirmasi di SKM, lalu telusuri nama dan logo melalui PDKI.'} />
        </div>

        <div className="grid gap-6 lg:grid-cols-[0.9fr_1.1fr]">
          <form onSubmit={handleSubmit} noValidate className="rounded-2xl border border-gov-line bg-white p-5 shadow-soft">
            <div className="mb-5 flex items-start gap-3 rounded-xl border border-blue-200 bg-blue-50 p-4 text-sm leading-6 text-blue-950">
              <ShieldCheck className="mt-0.5 shrink-0 text-gov-blue" size={20} aria-hidden="true" />
              <p>{mode === 'similarity'
                ? <><strong>Batas fungsi:</strong> angka hanya menunjukkan kedekatan teknis pada data pembanding portal, bukan probabilitas diterima, pendapat hukum, atau keputusan DJKI.</>
                : <><strong>Batas fungsi:</strong> sistem hanya membantu klasifikasi. Sistem tidak membandingkan merek, tidak menilai logo, dan tidak memprediksi diterima atau ditolak.</>}</p>
            </div>

            <div className="space-y-5">
              <div>
                <label htmlFor="nama_merek" className="block text-sm font-bold text-gov-navy">Nama merek</label>
                <input
                  ref={nameInputRef}
                  id="nama_merek"
                  value={form.nama_merek}
                  onChange={(event) => {
                    setForm({ ...form, nama_merek: event.target.value })
                    setFieldErrors((current) => ({ ...current, nama_merek: '' }))
                  }}
                  className={`mt-2 min-h-12 w-full rounded-lg border px-3 outline-none focus:border-gov-teal focus:ring-2 focus:ring-gov-mint ${fieldErrors.nama_merek ? 'border-red-500' : 'border-gov-line'}`}
                  placeholder="Contoh: Kopi Sembalun"
                  aria-invalid={Boolean(fieldErrors.nama_merek)}
                  aria-describedby={fieldErrors.nama_merek ? 'nama-merek-error' : 'nama-merek-help'}
                />
                <p id="nama-merek-help" className="mt-2 text-xs leading-5 text-slate-500">{mode === 'similarity' ? 'Nama dibandingkan dengan data pembanding lokal pada kelas yang direkomendasikan.' : 'Nama dicatat sebagai konteks layanan, bukan dianalisis kemiripannya.'}</p>
                {fieldErrors.nama_merek ? <p id="nama-merek-error" className="mt-2 text-sm font-semibold text-red-700">{fieldErrors.nama_merek}</p> : null}
              </div>

              <div>
                <label htmlFor="deskripsi_produk" className="block text-sm font-bold text-gov-navy">Deskripsi produk/jasa</label>
                <textarea
                  ref={descriptionInputRef}
                  id="deskripsi_produk"
                  value={form.deskripsi_produk}
                  onChange={(event) => {
                    setForm({ ...form, deskripsi_produk: event.target.value })
                    setFieldErrors((current) => ({ ...current, deskripsi_produk: '' }))
                  }}
                  className={`mt-2 min-h-44 w-full rounded-lg border px-3 py-3 outline-none focus:border-gov-teal focus:ring-2 focus:ring-gov-mint ${fieldErrors.deskripsi_produk ? 'border-red-500' : 'border-gov-line'}`}
                  placeholder="Contoh: Kami memproduksi kopi bubuk dalam kemasan dan menjual minuman kopi siap saji di kedai."
                  aria-invalid={Boolean(fieldErrors.deskripsi_produk)}
                  aria-describedby="deskripsi-help"
                />
                {fieldErrors.deskripsi_produk ? <p className="mt-2 text-sm font-semibold text-red-700">{fieldErrors.deskripsi_produk}</p> : null}
                <div className="mt-2 flex items-start gap-3">
                  <SpeechToTextButton
                    value={form.deskripsi_produk}
                    onChange={(value) => setForm({ ...form, deskripsi_produk: value })}
                    disabled={isLoading}
                  />
                  <p id="deskripsi-help" className="pt-2 text-xs leading-5 text-slate-500">Sebutkan bentuk, fungsi, pengguna, serta apakah Anda memproduksi, menjual, atau memberi layanan.</p>
                </div>
              </div>

              <div>
                <div className="flex items-center justify-between gap-3">
                  <label htmlFor="logo_merek" className="block text-sm font-bold text-gov-navy">Logo/etiket <span className="font-normal text-slate-500">(opsional)</span></label>
                  <span className="text-xs text-slate-500">PNG/JPEG, maks. 5 MB</span>
                </div>
                {logoPreview ? (
                  <div className="mt-2 flex items-center gap-4 rounded-xl border border-gov-line bg-gov-paper p-3">
                    <img src={logoPreview} alt="Pratinjau logo pilihan" className="h-24 w-24 rounded-lg border bg-white object-contain p-2" />
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-sm font-bold text-gov-navy">{logoFile.name}</p>
                      <p className="mt-1 text-xs leading-5 text-slate-600">{mode === 'similarity' ? 'Logo dikirim sementara untuk dianalisis dan tidak disimpan sebagai file pengguna.' : 'Hanya pratinjau di perangkat Anda. Logo tidak dikirim, disimpan, atau dinilai AI.'}</p>
                    </div>
                    <button type="button" onClick={() => setLogoFile(null)} className="rounded-full border border-gov-line bg-white p-2 text-slate-600 hover:text-red-600" aria-label="Hapus logo"><X size={18} /></button>
                  </div>
                ) : (
                  <label htmlFor="logo_merek" className="mt-2 flex cursor-pointer items-center gap-4 rounded-xl border-2 border-dashed border-gov-line bg-gov-paper p-4 transition hover:border-gov-teal hover:bg-teal-50">
                    <span className="flex h-12 w-12 items-center justify-center rounded-xl bg-white text-gov-teal shadow-sm"><ImagePlus size={24} /></span>
                    <span>
                      <span className="block text-sm font-bold text-gov-navy">Pilih file logo untuk pratinjau</span>
                      <span className="mt-1 block text-xs text-slate-600">{mode === 'similarity' ? 'Jika dipilih, visual dibandingkan dengan etiket referensi lokal yang tersedia.' : 'Logo tetap berada di browser dan perlu ditelusuri sendiri melalui PDKI.'}</span>
                    </span>
                  </label>
                )}
                <input id="logo_merek" type="file" accept="image/png,image/jpeg" onChange={handleLogoChange} className="sr-only" />
              </div>

              <button type="submit" disabled={isLoading} className="inline-flex min-h-14 w-full items-center justify-center gap-3 rounded-xl bg-gov-teal px-5 font-black text-white transition hover:bg-teal-700 disabled:cursor-not-allowed disabled:bg-slate-400">
                {isLoading ? <Loader2 className="animate-spin" size={21} /> : <BookOpenCheck size={21} />}
                {isLoading ? 'Sedang menganalisis' : mode === 'similarity' ? 'Jalankan AI Cek Merek' : 'Dapatkan rekomendasi kelas'}
              </button>
            </div>
          </form>

          <div ref={feedbackRef} tabIndex="-1" className="space-y-4 focus:outline-none" aria-label="Hasil rekomendasi klasifikasi">
            <div className="sr-only" aria-live="polite" aria-atomic="true">
              {isLoading ? 'Data sedang dianalisis.' : error ? `Analisis gagal. ${error}` : result ? 'Hasil analisis tersedia.' : ''}
            </div>

            {error ? <StatusNotice tone="error" title="Analisis belum berhasil">{error}</StatusNotice> : null}

            {isLoading ? (
              <div className="rounded-2xl border border-gov-line bg-white p-5 shadow-soft">
                <p className="font-black text-gov-navy">Sedang mencari klasifikasi yang relevan</p>
                <div className="mt-4 space-y-3">
                  {(mode === 'similarity'
                    ? ['Menentukan kelas dari deskripsi', 'Membandingkan nama dan logo', 'Menyiapkan kandidat pembanding']
                    : ['Memahami jenis dan fungsi barang/jasa', 'Mencocokkan dengan istilah resmi', 'Menyusun beberapa rekomendasi kelas']).map((step) => (
                    <div key={step} className="flex items-center gap-3 rounded-lg bg-gov-paper p-3 text-sm text-slate-700">
                      <Loader2 className="animate-spin text-gov-teal" size={17} /> {step}
                    </div>
                  ))}
                </div>
              </div>
            ) : null}

            {!result && !isLoading ? (
              <StatusNotice title={mode === 'similarity' ? 'Indikator akan tampil di sini' : 'Rekomendasi akan tampil di sini'}>
                {mode === 'similarity' ? 'Sistem akan menampilkan kandidat pembanding dari data lokal, indikator nama/visual, sumber, dan tautan verifikasi PDKI.' : 'Anda akan memperoleh beberapa kelas paling relevan, istilah barang/jasa resmi sebagai rincian, opsi rangkaian kelas, alasan rekomendasi, dan langkah verifikasi.'}
              </StatusNotice>
            ) : null}

            {result && !isLoading && mode === 'classification' ? (
              <ClassificationResult
                result={result}
                additionalDetail={additionalDetail}
                onAdditionalDetailChange={setAdditionalDetail}
                onClarify={handleClarification}
                onEscalate={handleEscalateClass}
                isEscalating={isEscalating}
                escalation={escalation}
                emailPengguna={emailPengguna}
                onEmailPenggunaChange={setEmailPengguna}
              />
            ) : null}
            {result && !isLoading && mode === 'similarity' ? <SimilarityResult result={result} /> : null}
          </div>
        </div>
      </section>
    </>
  )
}

function FlowStep({ number, title, text }) {
  return (
    <div className="flex gap-3 rounded-xl border border-gov-line bg-white p-4">
      <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-gov-royal font-black text-white">{number}</span>
      <div><p className="font-black text-gov-navy">{title}</p><p className="mt-1 text-xs leading-5 text-slate-600">{text}</p></div>
    </div>
  )
}

function ClassificationResult({ result, additionalDetail, onAdditionalDetailChange, onClarify, onEscalate, isEscalating, escalation, emailPengguna, onEmailPenggunaChange }) {
  const recommendations = result.rekomendasi_kelas || []
  return (
    <div className="space-y-4">
      <div className="rounded-2xl border border-gov-line bg-white p-5 shadow-soft">
        <div className="flex items-start justify-between gap-4">
          <div>
            <p className="text-xs font-black uppercase tracking-wider text-gov-blue">Rekomendasi untuk {result.nama_merek}</p>
            <h2 className="mt-2 text-xl font-black text-gov-navy">Kelas dan istilah barang/jasa yang relevan</h2>
            <p className="mt-2 text-sm leading-6 text-slate-600">Urutan menunjukkan tingkat kecocokan deskripsi dengan istilah resmi, bukan peluang merek diterima. Nice tidak memakai subkelas formal; nomor dasar barang/jasa ditampilkan sebagai rincian yang perlu dikonfirmasi di SKM.</p>
          </div>
          <BookOpenCheck className="shrink-0 text-gov-teal" size={28} />
        </div>

        {recommendations.length ? (
          <div className="mt-5 space-y-4">
            {recommendations.map((option, index) => (
              <ClassRecommendation key={`${option.kelas}-${index}`} option={option} rank={index + 1} />
            ))}
          </div>
        ) : (
          <StatusNotice tone="warning" title="Belum ada kelas yang cukup relevan">
            Tambahkan uraian mengenai bentuk, fungsi, tujuan penggunaan, dan cara usaha Anda menyediakan produk atau jasa.
          </StatusNotice>
        )}
        {(result.rangkaian_kelas || []).length > 1 ? (
          <div className="mt-5 rounded-xl border border-amber-200 bg-amber-50 p-4">
            <p className="text-sm font-black text-amber-950">Opsi rangkaian kelas</p>
            <p className="mt-1 text-xs leading-5 text-amber-900">Pertimbangkan hanya kelas yang benar-benar sesuai barang/jasa. Setiap kelas diajukan dan dikenai biaya secara terpisah.</p>
            <div className="mt-3 flex flex-wrap gap-2">
              {(result.rangkaian_kelas || []).map((item) => (
                <span key={item.kelas} className="rounded-full bg-white px-3 py-1 text-xs font-black text-gov-navy">Kelas {item.kelas}</span>
              ))}
            </div>
          </div>
        ) : null}
      </div>

      {result.perlu_klarifikasi ? (
        <div className="rounded-2xl border border-amber-200 bg-amber-50 p-5">
          <div className="flex items-start gap-3">
            <CircleHelp className="mt-0.5 shrink-0 text-amber-700" size={23} />
            <div>
              <p className="font-black text-amber-950">Informasi tambahan akan membuat hasil lebih tepat</p>
              <p className="mt-1 text-sm leading-6 text-amber-900">{result.pertanyaan_klarifikasi}</p>
            </div>
          </div>
          <textarea
            value={additionalDetail}
            onChange={(event) => onAdditionalDetailChange(event.target.value)}
            className="mt-4 min-h-24 w-full rounded-lg border border-amber-200 bg-white px-3 py-3 text-sm outline-none focus:border-gov-teal focus:ring-2 focus:ring-gov-mint"
            placeholder="Contoh: dijual sebagai kopi bubuk kemasan; kami juga menyediakan jasa kedai untuk pelanggan makan dan minum di tempat."
          />
          <button type="button" onClick={onClarify} className="mt-3 inline-flex min-h-11 w-full items-center justify-center gap-2 rounded-lg bg-amber-700 px-4 text-sm font-black text-white hover:bg-amber-800">
            <SearchCheck size={18} /> Analisis ulang dengan informasi tambahan
          </button>
        </div>
      ) : null}

      <div className="rounded-2xl border border-amber-200 bg-amber-50 p-5">
        <p className="font-black text-amber-950">Masih ragu dengan kelas atau uraian?</p>
        <p className="mt-1 text-sm leading-6 text-amber-900">Sesuai SOP, hasil ini dapat diteruskan kepada Petugas Helpdesk KI untuk ditinjau. Petugas memberi arahan awal berdasarkan sumber resmi, bukan keputusan pemeriksaan DJKI.</p>
        <label htmlFor="email-konsultasi" className="mt-3 block text-sm font-bold text-amber-950">Email untuk menerima pembaruan (opsional)</label>
        <input id="email-konsultasi" type="email" value={emailPengguna} onChange={(event) => onEmailPenggunaChange(event.target.value)} className="mt-1 min-h-11 w-full rounded-lg border border-amber-300 bg-white px-3 text-sm outline-none focus:border-gov-teal focus:ring-2 focus:ring-gov-mint" placeholder="nama@contoh.go.id" />
        <button type="button" onClick={onEscalate} disabled={isEscalating || Boolean(escalation)} className="mt-3 inline-flex min-h-11 items-center justify-center gap-2 rounded-lg bg-amber-700 px-4 text-sm font-black text-white hover:bg-amber-800 disabled:cursor-not-allowed disabled:opacity-60">
          {isEscalating ? <Loader2 className="animate-spin" size={18} /> : <MessageCircle size={18} />}
          {escalation ? 'Sudah diteruskan ke petugas' : 'Minta bantuan Petugas Helpdesk KI'}
        </button>
        {escalation ? (
          <div className="mt-3 rounded-lg border border-amber-300 bg-white p-3 text-sm text-amber-950">
            <p className="font-black">Nomor konsultasi: {escalation.kode_konsultasi}</p>
            <p className="mt-1">Status: {escalation.status_label}</p>
            <Link to={`/status-konsultasi/${escalation.pelacakan_id}`} className="mt-2 inline-flex font-bold text-gov-blue hover:underline">Pantau tindak lanjut petugas -&gt;</Link>
          </div>
        ) : null}
      </div>

      <div className="rounded-2xl border border-blue-200 bg-blue-50 p-5">
        <div className="flex items-start gap-3">
          <Info className="mt-0.5 shrink-0 text-gov-blue" size={22} />
          <div>
            <p className="font-black text-gov-navy">Langkah yang tetap perlu Anda lakukan</p>
            <ol className="mt-3 list-decimal space-y-2 pl-5 text-sm leading-6 text-slate-700">
              {(result.langkah_selanjutnya || []).map((item) => <li key={item}>{item}</li>)}
            </ol>
          </div>
        </div>
        <div className="mt-5 grid gap-3 sm:grid-cols-2">
          <a href={OFFICIAL_LINKS.skm} target="_blank" rel="noreferrer" className="inline-flex min-h-12 items-center justify-center gap-2 rounded-xl border border-gov-blue bg-white px-4 text-center text-sm font-black text-gov-blue hover:bg-blue-100">
            Konfirmasi di SKM DJKI <ExternalLink size={16} />
          </a>
          <a href={OFFICIAL_LINKS.pdki} target="_blank" rel="noreferrer" className="inline-flex min-h-12 items-center justify-center gap-2 rounded-xl bg-gov-royal px-4 text-center text-sm font-black text-white hover:bg-blue-900">
            Telusuri resmi di PDKI <ExternalLink size={16} />
          </a>
        </div>
      </div>

      <div className="grid gap-3 sm:grid-cols-2">
        <Link to="/chatbot" className="flex min-h-20 items-center gap-3 rounded-2xl border border-gov-line bg-white p-4 font-black text-gov-navy shadow-soft hover:border-gov-blue">
          <MessageCircle className="text-gov-teal" size={24} /> Tanya Chatbot Helpdesk
        </Link>
        <a href={HELPDESK_WHATSAPP_URL} target="_blank" rel="noreferrer" className="flex min-h-20 items-center gap-3 rounded-2xl bg-[#128c4a] p-4 font-black text-white shadow-soft hover:bg-[#0f7a40]">
          <MessageCircle size={24} /> Konsultasi dengan petugas
        </a>
      </div>

      <StatusNotice tone="warning" title="Batas hasil rekomendasi">
        {result.disclaimer}
      </StatusNotice>
    </div>
  )
}

function SimilarityResult({ result }) {
  if (result.perlu_klarifikasi && !result.kandidat_pembanding) {
    return (
      <StatusNotice tone="warning" title="Deskripsi perlu diperjelas">
        {result.pertanyaan_klarifikasi || result.detail}
      </StatusNotice>
    )
  }

  const candidates = result.kandidat_pembanding || []
  const attentionLabels = {
    rendah: 'Indikator awal rendah',
    sedang: 'Perlu ditinjau',
    tinggi: 'Perlu perhatian lebih',
  }
  return (
    <div className="space-y-4">
      <div className="rounded-2xl border border-gov-line bg-white p-5 shadow-soft">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="text-xs font-black uppercase tracking-wider text-gov-blue">Hasil AI Cek Merek</p>
            <h2 className="mt-2 text-xl font-black text-gov-navy">{attentionLabels[result.tingkat_perhatian] || 'Indikator awal'}</h2>
            <p className="mt-2 text-sm leading-6 text-slate-600">Kelas yang digunakan: {(result.kelas_nice_dianalisis || []).map((value) => `Kelas ${value}`).join(', ') || 'belum tersedia'}.</p>
          </div>
          <div className="rounded-2xl bg-blue-50 px-5 py-3 text-center">
            <p className="text-3xl font-black text-gov-blue">{result.indikator_tertinggi || 0}%</p>
            <p className="text-[11px] font-bold uppercase tracking-wide text-slate-600">indikator tertinggi</p>
          </div>
        </div>
        <div className="mt-4 flex items-start gap-3 rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm leading-6 text-amber-950">
          <ShieldAlert className="mt-0.5 shrink-0" size={21} />
          <p>Persentase adalah kedekatan teknis pada data yang tersedia, bukan peluang diterima atau ditolak. Data portal bukan salinan lengkap dan terkini dari seluruh PDKI.</p>
        </div>
        {result.perlu_klarifikasi_kelas ? (
          <p className="mt-3 rounded-xl bg-gov-paper p-3 text-xs leading-5 text-slate-700"><strong>Catatan kelas:</strong> {result.pertanyaan_klarifikasi || 'Deskripsi dapat diperjelas agar kelas yang dibandingkan lebih tepat.'}</p>
        ) : null}
      </div>

      <div className="rounded-2xl border border-gov-line bg-white p-5 shadow-soft">
        <h2 className="font-black text-gov-navy">Kandidat pembanding pada data portal</h2>
        <p className="mt-1 text-sm leading-6 text-slate-600">Maksimal sepuluh hasil di atas ambang teknis ditampilkan. Tidak muncul di sini bukan berarti merek pasti tersedia.</p>
        {result.cakupan_data ? (
          <div className="mt-4 grid grid-cols-2 gap-2 text-center sm:grid-cols-4">
            <CoverageMetric label="Data pada kelas" value={result.cakupan_data.total_data_kelas} />
            <CoverageMetric label="Ada nomor" value={result.cakupan_data.nomor_permohonan_tersedia} />
            <CoverageMetric label="Ada uraian" value={result.cakupan_data.uraian_barang_jasa_tersedia} />
            <CoverageMetric label="Ada etiket" value={result.cakupan_data.etiket_tersedia} />
          </div>
        ) : null}
        <div className="mt-4 rounded-xl border border-blue-200 bg-blue-50 p-4 text-xs leading-5 text-blue-950">
          Nama yang sama dengan uraian berbeda masih perlu ditinjau berdasarkan hubungan barang/jasa, kelas, daya pembeda, dan ketentuan pemeriksaan. Perbedaan uraian tidak otomatis berarti merek dapat didaftarkan.
        </div>
        {candidates.length ? (
          <div className="mt-4 space-y-3">
            {candidates.map((item) => (
              <article key={`${item.id}-${item.kelas}`} className="rounded-xl border border-gov-line bg-gov-paper p-4">
                <div className="flex items-start gap-3">
                  {item.label_merek_url ? <img src={item.label_merek_url} alt={`Etiket pembanding ${item.nama}`} className="h-16 w-16 shrink-0 rounded-lg border border-gov-line bg-white object-contain p-1" /> : null}
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-start justify-between gap-2">
                      <div>
                        <h3 className="break-words font-black text-gov-navy">{item.nama}</h3>
                        <p className="mt-1 text-xs font-bold text-gov-blue">Nomor permohonan: {item.nomor_permohonan || 'Belum tersedia'}</p>
                        <p className="mt-1 text-xs text-slate-600">Kelas {item.kelas} · {item.status}</p>
                        <span className={`mt-2 inline-flex rounded-full px-2 py-1 text-[11px] font-black ${item.kelas_sesuai_rekomendasi === false ? 'bg-amber-100 text-amber-900' : 'bg-emerald-100 text-emerald-900'}`}>
                          {item.kelas_sesuai_rekomendasi === false ? 'Kelas berbeda, tetap perlu ditinjau' : 'Sesuai kelas yang dianalisis'}
                        </span>
                      </div>
                      <span className="rounded-full bg-white px-3 py-1 text-xs font-black text-gov-blue">Gabungan {item.skor_gabungan ?? item.skor_kemiripan}%</span>
                    </div>
                    <div className="mt-3 flex flex-wrap gap-2 text-xs font-bold text-slate-700">
                      <span className="rounded-lg bg-white px-2 py-1">Nama {item.skor_kemiripan}%</span>
                      <span className="rounded-lg bg-white px-2 py-1">Barang/jasa {item.skor_kesesuaian_barang_jasa == null ? 'belum dinilai' : `${item.skor_kesesuaian_barang_jasa}%`}</span>
                      <span className="rounded-lg bg-white px-2 py-1">Visual {item.skor_visual == null ? 'tidak tersedia' : `${item.skor_visual}%`}</span>
                    </div>
                    <dl className="mt-3 grid gap-2 text-xs sm:grid-cols-2">
                      <div className="rounded-lg bg-white p-3"><dt className="font-bold text-slate-500">Pemilik</dt><dd className="mt-1 font-semibold leading-5 text-gov-navy">{item.pemilik || 'Belum tersedia'}</dd></div>
                      <div className="rounded-lg bg-white p-3"><dt className="font-bold text-slate-500">Hubungan barang/jasa</dt><dd className="mt-1 font-semibold leading-5 text-gov-navy">{item.hubungan_barang_jasa || 'Belum dinilai'}</dd></div>
                      <div className="rounded-lg bg-white p-3"><dt className="font-bold text-slate-500">Tanggal penerimaan</dt><dd className="mt-1 font-semibold text-gov-navy">{formatDate(item.tanggal_penerimaan)}</dd></div>
                      <div className="rounded-lg bg-white p-3"><dt className="font-bold text-slate-500">Tanggal publikasi</dt><dd className="mt-1 font-semibold text-gov-navy">{formatDate(item.tanggal_publikasi)}</dd></div>
                    </dl>
                    <div className="mt-3 rounded-lg border border-gov-line bg-white p-3">
                      <p className="text-xs font-black uppercase tracking-wide text-gov-blue">Uraian barang/jasa pembanding</p>
                      <p className="mt-2 whitespace-pre-line text-sm leading-6 text-slate-700">{item.uraian_barang_jasa || 'Uraian belum tersedia pada data mirror. Buka sumber resmi untuk memeriksa rincian permohonan.'}</p>
                    </div>
                    {(item.alasan_kemiripan || []).length ? <ul className="mt-3 list-disc space-y-1 pl-5 text-xs leading-5 text-slate-700">{item.alasan_kemiripan.map((reason) => <li key={reason}>{reason}</li>)}</ul> : null}
                    {item.sumber_data_url ? <a href={item.sumber_data_url} target="_blank" rel="noreferrer" className="mt-3 inline-flex items-center gap-1 text-xs font-black text-gov-blue hover:underline">Buka sumber DJKI <ExternalLink size={13} /></a> : null}
                  </div>
                </div>
              </article>
            ))}
          </div>
        ) : <p className="mt-4 rounded-xl bg-gov-paper p-4 text-sm leading-6 text-slate-700">Tidak ada kandidat di atas ambang pada data lokal yang tersedia. Tetap lakukan pencarian teks dan gambar di PDKI.</p>}
      </div>

      <a href={OFFICIAL_LINKS.pdki} target="_blank" rel="noreferrer" className="flex min-h-14 items-center justify-center gap-2 rounded-xl bg-gov-royal px-5 text-center font-black text-white hover:bg-blue-900">
        Verifikasi nama dan gambar di PDKI <ExternalLink size={17} />
      </a>
      <StatusNotice tone="warning" title="Disclaimer penting">{result.disclaimer}</StatusNotice>
    </div>
  )
}

function CoverageMetric({ label, value }) {
  return <div className="rounded-xl bg-gov-paper p-3"><p className="text-xl font-black text-gov-navy">{Number(value || 0).toLocaleString('id-ID')}</p><p className="mt-1 text-[11px] font-bold text-slate-600">{label}</p></div>
}

function formatDate(value) {
  if (!value) return 'Belum tersedia'
  return new Date(`${value}T00:00:00`).toLocaleDateString('id-ID', {
    day: 'numeric', month: 'long', year: 'numeric',
  })
}

function ClassRecommendation({ option, rank }) {
  const relevance = Math.round(Number(option.keyakinan || 0) * 100)
  return (
    <article className="overflow-hidden rounded-xl border border-gov-line">
      <div className="flex flex-wrap items-center justify-between gap-3 bg-gov-paper px-4 py-3">
        <div className="flex items-center gap-3">
          <span className="flex h-8 w-8 items-center justify-center rounded-full bg-gov-royal text-sm font-black text-white">{rank}</span>
          <h3 className="text-lg font-black text-gov-navy">Kelas {option.kelas}</h3>
        </div>
        <span className="rounded-full bg-white px-3 py-1 text-xs font-black text-gov-blue">Relevansi deskripsi {relevance}%</span>
      </div>
      <div className="p-4">
        <p className="text-sm font-bold leading-6 text-gov-navy">{option.alasan}</p>
        <p className="mt-2 text-sm leading-6 text-slate-600">{option.deskripsi_kelas}</p>
        {(option.istilah_resmi || []).length ? (
          <div className="mt-4 rounded-xl border border-blue-100 bg-blue-50 p-3">
            <p className="text-xs font-black uppercase tracking-wide text-gov-blue">Rincian barang/jasa (istilah resmi dan nomor dasar)</p>
            <ul className="mt-2 space-y-2 text-sm leading-5 text-slate-700">
              {option.istilah_resmi.map((term) => (
                <li key={`${term.basic_number}-${term.istilah}`} className="flex items-start gap-2">
                  <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-gov-gold" />
                  <span><strong>{term.istilah}</strong> <span className="text-xs text-slate-500">Nomor dasar {term.basic_number}</span></span>
                </li>
              ))}
            </ul>
          </div>
        ) : null}
        <div className="mt-4 flex flex-wrap gap-x-4 gap-y-2 text-xs font-black text-gov-blue">
          {option.skm_url ? <a href={option.skm_url} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 hover:underline">Buka Kelas {option.kelas} di SKM <ExternalLink size={13} /></a> : null}
          {option.sumber_url ? <a href={option.sumber_url} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 hover:underline">Lihat sumber resmi <ExternalLink size={13} /></a> : null}
        </div>
      </div>
    </article>
  )
}


