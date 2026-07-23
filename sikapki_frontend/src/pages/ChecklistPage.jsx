import { useEffect, useMemo, useState } from 'react'
import { Check, CheckCircle2, ClipboardCheck, ExternalLink, Printer, RotateCcw, Save } from 'lucide-react'
import PageHeader from '../components/PageHeader.jsx'
import { OFFICIAL_LINKS } from '../config/service.js'

const applicantTypes = {
  perorangan: 'Perorangan/umum',
  umk: 'Usaha Mikro atau Usaha Kecil',
  badan: 'Badan hukum/lembaga',
}

const services = {
  merek: {
    label: 'Merek', source: OFFICIAL_LINKS.merek,
    note: 'Persiapan permohonan merek baru. Dokumen UMK hanya muncul bagi pemohon UMK.',
    items: [
      item('etiket', 'Etiket atau label merek'),
      item('tanda-tangan', 'Tanda tangan pemohon'),
      item('identitas', 'Data identitas pemohon dan alamat korespondensi'),
      item('barang-jasa', 'Daftar barang/jasa serta kelas Nice yang dipilih'),
      item('rekomendasi-umk', 'Surat rekomendasi atau keterangan UMK binaan', ['umk']),
      item('pernyataan-umk', 'Surat pernyataan UMK bermeterai', ['umk']),
      item('akta', 'Akta pendirian dan perubahan terakhir', ['badan']),
    ],
  },
  hakCipta: {
    label: 'Hak Cipta', source: OFFICIAL_LINKS.hakCipta,
    note: 'Persiapan pencatatan ciptaan atau produk hak terkait.',
    items: [
      item('pencipta', 'Identitas pencipta dan pemegang hak cipta'),
      item('uraian', 'Judul dan uraian singkat ciptaan'),
      item('pengumuman', 'Tanggal, kota, dan negara pertama kali diumumkan'),
      item('contoh', 'Contoh ciptaan sesuai jenis karya'),
      item('pernyataan', 'Surat pernyataan kepemilikan ciptaan'),
      item('pengalihan', 'Surat pengalihan hak bila pencipta dan pemegang hak berbeda'),
      item('akta', 'Akta pendirian dan perubahan terakhir', ['badan']),
    ],
  },
  paten: {
    label: 'Paten', source: OFFICIAL_LINKS.paten,
    note: 'Dokumen teknis harus konsisten satu sama lain sebelum diajukan.',
    items: [
      item('deskripsi', 'Deskripsi permohonan paten dalam Bahasa Indonesia'),
      item('klaim', 'Klaim invensi'), item('abstrak', 'Abstrak'),
      item('gambar', 'Gambar invensi PDF dan gambar publikasi JPG'),
      item('kepemilikan', 'Surat pernyataan kepemilikan invensi'),
      item('pengalihan', 'Surat pengalihan hak bila inventor dan pemohon berbeda'),
      item('umk', 'Surat keterangan UMK bila menggunakan tarif UMK', ['umk']),
      item('akta', 'Akta pendirian untuk badan hukum atau lembaga', ['badan']),
    ],
  },
  desain: {
    label: 'Desain Industri', source: OFFICIAL_LINKS.desainIndustri,
    note: 'Pastikan gambar memperlihatkan desain secara jelas dan konsisten.',
    items: [
      item('gambar', 'Gambar desain industri dari sudut yang dipersyaratkan'),
      item('uraian', 'Uraian desain industri'),
      item('kepemilikan', 'Surat pernyataan kepemilikan desain'),
      item('pengalihan', 'Surat pengalihan hak bila pemohon dan pendesain berbeda'),
      item('identitas', 'Identitas pemohon dan pendesain'),
      item('umk', 'Surat keterangan UMK bila menggunakan tarif UMK', ['umk']),
      item('akta', 'Akta pendirian untuk badan hukum atau lembaga', ['badan']),
    ],
  },
}

function item(id, label, audiences = ['all']) { return { id, label, audiences } }

export default function ChecklistPage() {
  const [active, setActive] = useState('merek')
  const [applicant, setApplicant] = useState('perorangan')
  const [checked, setChecked] = useState(loadProgress)
  const service = services[active]
  const visibleItems = useMemo(() => service.items.filter((entry) => entry.audiences.includes('all') || entry.audiences.includes(applicant)), [service, applicant])
  const keyFor = (entry) => `${active}:${applicant}:${entry.id}`
  const completed = visibleItems.filter((entry) => checked[keyFor(entry)]).length
  const progress = visibleItems.length ? Math.round((completed / visibleItems.length) * 100) : 0

  useEffect(() => { localStorage.setItem('sikapki-checklist-v2', JSON.stringify(checked)) }, [checked])

  function toggle(entry) {
    const key = keyFor(entry)
    setChecked((current) => ({ ...current, [key]: !current[key] }))
  }

  function resetActive() {
    const prefix = `${active}:${applicant}:`
    setChecked((current) => Object.fromEntries(Object.entries(current).filter(([key]) => !key.startsWith(prefix))))
  }

  return (
    <>
      <PageHeader eyebrow="Checklist interaktif" title="Siapkan dokumen sesuai profil pemohon" description="Pilih jenis pemohon, centang dokumen yang tersedia, lalu cetak ringkasan persiapan. Checklist bukan validasi formal permohonan." />
      <section className="mx-auto max-w-6xl px-4 py-10">
        <div className="rounded-2xl border border-gov-line bg-white p-5 shadow-soft print:border-0 print:shadow-none">
          <p className="text-sm font-black uppercase tracking-wider text-gov-blue">1. Pilih jenis pemohon</p>
          <div className="mt-3 flex flex-wrap gap-2 print:hidden">
            {Object.entries(applicantTypes).map(([key, label]) => <button key={key} type="button" onClick={() => setApplicant(key)} className={`rounded-xl border px-4 py-3 text-sm font-bold ${applicant === key ? 'border-gov-teal bg-teal-50 text-gov-teal ring-2 ring-gov-mint' : 'border-gov-line text-slate-700'}`}>{label}</button>)}
          </div>
          <p className="mt-3 hidden font-bold print:block">{applicantTypes[applicant]}</p>

          <p className="mt-7 text-sm font-black uppercase tracking-wider text-gov-blue">2. Pilih layanan KI</p>
          <div className="mt-3 flex gap-2 overflow-x-auto pb-2 print:hidden">
            {Object.entries(services).map(([key, entry]) => <button key={key} type="button" onClick={() => setActive(key)} className={`min-h-11 shrink-0 rounded-xl border px-5 font-extrabold ${active === key ? 'border-gov-blue bg-gov-blue text-white' : 'border-gov-line bg-white text-slate-700'}`}>{entry.label}</button>)}
          </div>

          <div className="mt-6 grid gap-6 lg:grid-cols-[0.68fr_1.32fr]">
            <aside className="rounded-2xl bg-gov-royal p-6 text-white print:bg-white print:p-0 print:text-black">
              <ClipboardCheck className="text-gov-gold print:hidden" size={36} />
              <p className="mt-5 text-sm font-bold uppercase tracking-widest text-blue-200 print:mt-0 print:text-black">Progres {service.label}</p>
              <p className="mt-2 text-6xl font-black">{progress}%</p>
              <div className="mt-5 h-3 overflow-hidden rounded-full bg-white/15 print:hidden"><div className="h-full rounded-full bg-gov-gold" style={{ width: `${progress}%` }} /></div>
              <p className="mt-4 text-sm leading-6 text-blue-100 print:text-black">{completed} dari {visibleItems.length} dokumen telah dicentang untuk {applicantTypes[applicant].toLowerCase()}.</p>
              <p className="mt-5 rounded-xl border border-white/15 bg-white/10 p-4 text-sm leading-6 text-blue-50 print:border-slate-300 print:bg-white print:text-black">{service.note}</p>
              <a href={service.source} target="_blank" rel="noreferrer" className="mt-5 inline-flex items-center gap-2 font-bold text-gov-gold print:text-black">Sumber resmi DJKI <ExternalLink size={17} /></a>
            </aside>

            <div>
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div><p className="text-sm font-bold uppercase tracking-wider text-gov-blue">Daftar persiapan</p><h2 className="mt-1 text-2xl font-black text-gov-navy">Permohonan {service.label}</h2></div>
                <div className="flex gap-2 print:hidden">
                  <button type="button" onClick={() => window.print()} className="inline-flex items-center gap-2 rounded-lg bg-gov-blue px-3 py-2 text-sm font-bold text-white"><Printer size={16} /> Cetak</button>
                  <button type="button" onClick={resetActive} className="inline-flex items-center gap-2 rounded-lg border border-gov-line px-3 py-2 text-sm font-bold text-slate-600"><RotateCcw size={16} /> Reset</button>
                </div>
              </div>
              <div className="mt-6 space-y-3">
                {visibleItems.map((entry) => {
                  const isChecked = Boolean(checked[keyFor(entry)])
                  return <button key={entry.id} type="button" onClick={() => toggle(entry)} className={`flex w-full items-start gap-4 rounded-xl border p-4 text-left ${isChecked ? 'border-emerald-300 bg-emerald-50' : 'border-gov-line bg-white'} print:break-inside-avoid`}><span className={`mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-lg border-2 ${isChecked ? 'border-emerald-600 bg-emerald-600 text-white' : 'border-slate-300 text-transparent'}`}><Check size={17} /></span><span className={`font-semibold leading-7 ${isChecked ? 'text-emerald-950' : 'text-slate-700'}`}>{entry.label}</span></button>
                })}
              </div>
              <div className="mt-5 flex items-center gap-2 rounded-xl bg-blue-50 p-3 text-xs leading-5 text-gov-blue print:hidden"><Save size={17} className="shrink-0" /> Progres tersimpan otomatis pada perangkat ini dan tidak dikirim ke server.</div>
              {progress === 100 ? <div className="mt-5 flex items-start gap-3 rounded-xl border border-emerald-300 bg-emerald-50 p-4 text-emerald-950"><CheckCircle2 className="mt-0.5 shrink-0" /><p className="text-sm leading-6"><strong>Persiapan awal selesai.</strong> Periksa format dan ketentuan terbaru pada sumber DJKI atau Helpdesk KI sebelum mengajukan.</p></div> : null}
            </div>
          </div>
        </div>
      </section>
    </>
  )
}

function loadProgress() {
  try { return JSON.parse(localStorage.getItem('sikapki-checklist-v2') || '{}') }
  catch { return {} }
}
