import { useEffect, useMemo, useState } from 'react'
import { FileQuestion, Loader2, Search } from 'lucide-react'
import PageHeader from '../components/PageHeader.jsx'
import StatusNotice from '../components/StatusNotice.jsx'
import { getFaq, getKategori, unwrapResults } from '../lib/api.js'

export default function FaqPage() {
  const [faqItems, setFaqItems] = useState([])
  const [categories, setCategories] = useState([])
  const [query, setQuery] = useState('')
  const [category, setCategory] = useState('semua')
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    let isMounted = true
    async function loadData() {
      try {
        const [faqData, categoryData] = await Promise.all([getFaq(), getKategori()])
        if (!isMounted) return
        setFaqItems(unwrapResults(faqData))
        setCategories(unwrapResults(categoryData))
      } catch (err) {
        if (isMounted) setError(err.message)
      } finally {
        if (isMounted) setIsLoading(false)
      }
    }
    loadData()
    return () => {
      isMounted = false
    }
  }, [])

  const filteredFaq = useMemo(() => {
    const needle = query.trim().toLowerCase()
    return faqItems.filter((item) => {
      const matchesCategory = category === 'semua' || String(item.kategori) === category
      const matchesSearch = !needle
        || item.pertanyaan?.toLowerCase().includes(needle)
        || item.jawaban?.toLowerCase().includes(needle)
        || item.kategori_nama?.toLowerCase().includes(needle)
      return matchesCategory && matchesSearch
    })
  }, [faqItems, query, category])

  return (
    <>
      <PageHeader
        eyebrow="FAQ"
        title="Pertanyaan yang sering diajukan"
        description="Cari jawaban singkat seputar layanan Kekayaan Intelektual. Gunakan filter kategori untuk mempersempit daftar."
      />
      <section className="mx-auto max-w-6xl px-4 py-8">
        <div className="rounded-lg border border-gov-line bg-white p-4 shadow-soft">
          <div className="grid gap-3 md:grid-cols-[1fr_260px]">
            <div>
              <label htmlFor="faq-search" className="block text-sm font-bold text-gov-navy">Cari FAQ</label>
              <div className="relative mt-2">
                <Search className="pointer-events-none absolute left-3 top-3.5 h-5 w-5 text-slate-400" aria-hidden="true" />
                <input
                  id="faq-search"
                  value={query}
                  onChange={(event) => setQuery(event.target.value)}
                  className="min-h-12 w-full rounded-md border border-gov-line pl-10 pr-3 outline-none focus:border-gov-teal focus:ring-2 focus:ring-gov-mint"
                  placeholder="Contoh: biaya merek UMKM"
                />
              </div>
            </div>
            <div>
              <label htmlFor="faq-category" className="block text-sm font-bold text-gov-navy">Kategori</label>
              <select
                id="faq-category"
                value={category}
                onChange={(event) => setCategory(event.target.value)}
                className="mt-2 min-h-12 w-full rounded-md border border-gov-line px-3 outline-none focus:border-gov-teal focus:ring-2 focus:ring-gov-mint"
              >
                <option value="semua">Semua kategori</option>
                {categories.map((item) => (
                  <option key={item.id} value={String(item.id)}>{item.nama}</option>
                ))}
              </select>
            </div>
          </div>
        </div>

        {error ? (
          <div className="mt-4">
            <StatusNotice tone="error" title="FAQ belum bisa dimuat">
              {error}
            </StatusNotice>
          </div>
        ) : null}

        {isLoading ? (
          <div className="mt-8 flex items-center gap-3 text-slate-600">
            <Loader2 className="h-5 w-5 animate-spin text-gov-teal" aria-hidden="true" />
            Memuat daftar FAQ...
          </div>
        ) : (
          <div className="mt-6 grid gap-4">
            <p className="text-sm text-slate-600">{filteredFaq.length} FAQ ditemukan</p>
            {filteredFaq.length ? filteredFaq.map((item) => (
              <article key={item.id} className="rounded-lg border border-gov-line bg-white p-5 shadow-soft">
                <div className="flex flex-col gap-2 md:flex-row md:items-start md:justify-between">
                  <div className="flex items-start gap-3">
                    <FileQuestion className="mt-1 h-5 w-5 shrink-0 text-gov-teal" aria-hidden="true" />
                    <div>
                      <h2 className="text-lg font-bold leading-7 text-gov-navy">{item.pertanyaan}</h2>
                      <p className="mt-3 whitespace-pre-line text-sm leading-7 text-slate-700">{item.jawaban}</p>
                    </div>
                  </div>
                  {item.kategori_nama ? (
                    <span className="shrink-0 rounded-md bg-gov-mint px-3 py-1 text-xs font-bold text-gov-navy">
                      {item.kategori_nama}
                    </span>
                  ) : null}
                </div>
              </article>
            )) : (
              <StatusNotice title="Tidak ada FAQ yang cocok">
                Coba gunakan kata kunci yang lebih umum atau pilih semua kategori.
              </StatusNotice>
            )}
          </div>
        )}
      </section>
    </>
  )
}
