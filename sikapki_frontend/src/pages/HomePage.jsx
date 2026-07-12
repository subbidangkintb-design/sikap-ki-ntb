import { Link } from 'react-router-dom'
import { ArrowRight, Building2, MessageSquareText, SearchCheck } from 'lucide-react'

export default function HomePage() {
  return (
    <>
      <section className="bg-white">
        <div className="mx-auto grid max-w-6xl gap-8 px-4 py-12 lg:grid-cols-[1.08fr_0.92fr] lg:items-center">
          <div>
            <p className="mb-3 text-sm font-bold uppercase tracking-wide text-gov-teal">Layanan AI Kekayaan Intelektual NTB</p>
            <h1 className="max-w-3xl text-4xl font-bold leading-tight text-gov-navy md:text-5xl">
              SIKAP-KI NTB
            </h1>
            <p className="mt-5 max-w-2xl text-lg leading-8 text-slate-700">
              Portal bantuan awal untuk masyarakat dan pelaku UMKM dalam memahami layanan Kekayaan Intelektual,
              mengecek risiko nama merek, dan bertanya berdasarkan dokumen pengetahuan resmi yang tersedia.
            </p>
            <div className="mt-8 grid gap-3 sm:grid-cols-2">
              <Link
                to="/cek-merek"
                className="inline-flex min-h-16 items-center justify-center gap-3 rounded-lg bg-gov-teal px-5 text-base font-bold text-white shadow-soft transition hover:bg-teal-700"
              >
                <SearchCheck size={22} aria-hidden="true" />
                Cek Nama Merek Saya
              </Link>
              <Link
                to="/chatbot"
                className="inline-flex min-h-16 items-center justify-center gap-3 rounded-lg border border-gov-blue bg-white px-5 text-base font-bold text-gov-blue transition hover:bg-gov-mint"
              >
                <MessageSquareText size={22} aria-hidden="true" />
                Tanya AI
              </Link>
            </div>
          </div>

          <div className="rounded-lg border border-gov-line bg-gov-mint p-6 shadow-soft">
            <div className="mb-5 flex items-center gap-3">
              <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-gov-navy text-white">
                <Building2 size={25} aria-hidden="true" />
              </div>
              <div>
                <p className="font-bold text-gov-navy">Untuk layanan publik yang lebih jelas</p>
                <p className="text-sm text-slate-600">Bantuan awal, bukan pengganti keputusan resmi.</p>
              </div>
            </div>
            <div className="grid gap-3">
              {[
                'Membantu mengarahkan kelas Nice yang relevan.',
                'Membandingkan nama merek dengan data mirror PDKI lokal.',
                'Menjawab pertanyaan umum berdasarkan knowledge base.',
              ].map((item) => (
                <div key={item} className="flex items-start gap-3 rounded-md bg-white p-3">
                  <ArrowRight className="mt-0.5 h-5 w-5 shrink-0 text-gov-teal" aria-hidden="true" />
                  <p className="text-sm leading-6 text-slate-700">{item}</p>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      <section className="border-y border-gov-line bg-gov-paper">
        <div className="mx-auto grid max-w-6xl gap-4 px-4 py-8 md:grid-cols-3">
          <InfoBlock title="Cek awal risiko" text="Dapatkan gambaran awal apakah nama merek berpotensi mirip dengan merek lain." />
          <InfoBlock title="Bahasa sederhana" text="Jawaban disusun agar mudah dipahami masyarakat umum dan pelaku usaha." />
          <InfoBlock title="Tetap transparan" text="Setiap hasil menampilkan disclaimer dan sumber konteks saat tersedia." />
        </div>
      </section>
    </>
  )
}

function InfoBlock({ title, text }) {
  return (
    <div className="rounded-lg border border-gov-line bg-white p-5">
      <h2 className="text-lg font-bold text-gov-navy">{title}</h2>
      <p className="mt-2 text-sm leading-6 text-slate-700">{text}</p>
    </div>
  )
}
