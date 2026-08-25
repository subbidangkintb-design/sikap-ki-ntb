import { useState } from 'react'
import { CheckCircle2, ClipboardList, Send } from 'lucide-react'
import PageHeader from '../components/PageHeader.jsx'
import StatusNotice from '../components/StatusNotice.jsx'
import { kirimUjiCoba } from '../lib/api.js'

const initial = {
  peran: 'masyarakat', layanan: 'keseluruhan', tugas_berhasil: true,
  kemudahan: 5, kejelasan: 5, kepercayaan: 5, kepuasan: 5,
  masukan: '', persetujuan: false,
}

const questions = [
  ['kemudahan', 'Seberapa mudah layanan digunakan?'],
  ['kejelasan', 'Seberapa jelas informasi dan hasil yang diberikan?'],
  ['kepercayaan', 'Seberapa yakin Anda terhadap arahan awal sistem?'],
  ['kepuasan', 'Seberapa puas Anda terhadap pengalaman keseluruhan?'],
]

export default function UserTestingPage() {
  const [form, setForm] = useState(initial)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [result, setResult] = useState(null)
  const change = (field, value) => setForm((current) => ({ ...current, [field]: value }))

  async function submit(event) {
    event.preventDefault()
    setLoading(true); setError('')
    try {
      setResult(await kirimUjiCoba(form))
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return <>
    <PageHeader eyebrow="Uji coba pengguna" title="Bantu kami menguji kesiapan SIKAP-KI NTB" description="Selesaikan satu tugas pada portal, lalu berikan evaluasi singkat. Respons disimpan tanpa nama dan dipakai sebagai bukti perbaikan layanan." />
    <section className="ministry-grid mx-auto max-w-4xl px-4 py-10">
      {result ? <div className="rounded-2xl border border-emerald-200 bg-emerald-50 p-8 text-center shadow-soft">
        <CheckCircle2 className="mx-auto text-emerald-700" size={44} />
        <h2 className="mt-4 text-2xl font-black text-emerald-950">Evaluasi berhasil direkam</h2>
        <p className="mt-2 text-emerald-900">Kode bukti: <strong>{result.kode_respons}</strong></p>
        <button className="mt-6 rounded-xl bg-gov-royal px-5 py-3 font-black text-white" onClick={() => { setResult(null); setForm(initial) }}>Isi evaluasi berikutnya</button>
      </div> : <form onSubmit={submit} className="rounded-2xl border border-gov-line bg-white p-6 shadow-ministry sm:p-8">
        <div className="flex items-start gap-3"><ClipboardList className="mt-1 shrink-0 text-gov-blue" /><div><h2 className="text-2xl font-black">Form evaluasi singkat</h2><p className="mt-1 text-sm leading-6 text-slate-600">Nilai 1 berarti sangat kurang dan 5 berarti sangat baik.</p></div></div>
        {error ? <div className="mt-5"><StatusNotice tone="error" title="Evaluasi belum tersimpan">{error}</StatusNotice></div> : null}
        <div className="mt-7 grid gap-5 sm:grid-cols-2">
          <Select label="Peran Anda" value={form.peran} onChange={(v) => change('peran', v)} options={[['masyarakat','Masyarakat/pemohon'],['umkm','Pelaku UMKM'],['petugas','Petugas layanan'],['lainnya','Lainnya']]} />
          <Select label="Layanan yang diuji" value={form.layanan} onChange={(v) => change('layanan', v)} options={[['keseluruhan','Keseluruhan portal'],['chatbot','Chatbot Helpdesk KI'],['cek_merek','Asisten klasifikasi awal merek'],['checklist','Checklist dokumen'],['informasi','Pusat informasi']]} />
        </div>
        <fieldset className="mt-6"><legend className="font-black">Apakah tugas yang Anda coba berhasil diselesaikan?</legend><div className="mt-3 flex gap-5"><Radio checked={form.tugas_berhasil} onChange={() => change('tugas_berhasil', true)} label="Ya, berhasil" /><Radio checked={!form.tugas_berhasil} onChange={() => change('tugas_berhasil', false)} label="Belum berhasil" /></div></fieldset>
        <div className="mt-7 space-y-6">{questions.map(([field, label]) => <fieldset key={field}><legend className="font-black">{label}</legend><div className="mt-3 flex flex-wrap gap-2">{[1,2,3,4,5].map((score) => <label key={score} className={`flex h-11 w-11 cursor-pointer items-center justify-center rounded-xl border-2 font-black ${form[field] === score ? 'border-gov-gold bg-amber-50 text-gov-navy' : 'border-slate-200 text-slate-600'}`}><input className="sr-only" type="radio" name={field} value={score} checked={form[field] === score} onChange={() => change(field, score)} />{score}</label>)}</div></fieldset>)}</div>
        <label className="mt-7 block font-black">Masukan atau kendala <span className="font-normal text-slate-500">(opsional)</span><textarea className="mt-2 min-h-28 w-full rounded-xl border border-slate-300 p-3 font-normal focus:border-gov-blue focus:outline-none focus:ring-2 focus:ring-blue-100" value={form.masukan} onChange={(e) => change('masukan', e.target.value)} maxLength={2000} placeholder="Tuliskan bagian yang sudah baik atau masih perlu diperbaiki." /></label>
        <label className="mt-5 flex items-start gap-3 rounded-xl bg-slate-50 p-4 text-sm leading-6"><input className="mt-1 h-5 w-5" type="checkbox" required checked={form.persetujuan} onChange={(e) => change('persetujuan', e.target.checked)} /><span>Saya menyetujui evaluasi anonim ini digunakan untuk perbaikan dan bukti uji coba SIKAP-KI NTB. Sistem tidak meminta nama, nomor telepon, atau alamat.</span></label>
        <button disabled={loading} className="mt-6 inline-flex min-h-12 w-full items-center justify-center gap-2 rounded-xl bg-gov-royal px-5 font-black text-white disabled:opacity-60"><Send size={19} />{loading ? 'Menyimpan...' : 'Kirim evaluasi'}</button>
      </form>}
    </section>
  </>
}

function Select({ label, value, onChange, options }) { return <label className="font-black">{label}<select className="mt-2 min-h-12 w-full rounded-xl border border-slate-300 bg-white px-3 font-normal" value={value} onChange={(e) => onChange(e.target.value)}>{options.map(([key, text]) => <option key={key} value={key}>{text}</option>)}</select></label> }
function Radio({ checked, onChange, label }) { return <label className="flex cursor-pointer items-center gap-2 font-bold"><input className="h-5 w-5" type="radio" checked={checked} onChange={onChange} />{label}</label> }
