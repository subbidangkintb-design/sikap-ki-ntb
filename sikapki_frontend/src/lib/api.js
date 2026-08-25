const configuredApiUrl = (import.meta.env.VITE_API_BASE_URL || '').trim()
const API_BASE_URL = (
  configuredApiUrl || `${window.location.protocol}//${window.location.hostname}:8000`
).replace(/\/$/, '')
const REQUEST_TIMEOUT_MS = 45_000

async function waitForBackgroundJob(queued, label) {
  if (!queued.job_id) return queued
  const deadline = Date.now() + 120_000
  while (Date.now() < deadline) {
    await new Promise((resolve) => window.setTimeout(resolve, 1000))
    const job = await request(`/api/core/jobs/${encodeURIComponent(queued.job_id)}/`)
    if (job.status === 'succeeded') return job.result
    if (job.status === 'failed') throw new Error(job.error || `${label} gagal diproses.`)
  }
  throw new Error(`Antrean ${label.toLowerCase()} belum selesai. Pastikan worker background job sedang berjalan.`)
}

async function request(path, options = {}) {
  const controller = new AbortController()
  const timeoutId = window.setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS)

  let response
  try {
    const isFormData = options.body instanceof FormData
    response = await fetch(`${API_BASE_URL}${path}`, {
      headers: {
        ...(isFormData ? {} : { 'Content-Type': 'application/json' }),
        ...(options.headers || {}),
      },
      ...options,
      signal: controller.signal,
    })
  } catch (error) {
    if (error.name === 'AbortError') {
      throw new Error(
        'Layanan AI melewati batas waktu 45 detik. Periksa koneksi internet dan layanan Gemini, lalu coba lagi.',
      )
    }
    throw error
  } finally {
    window.clearTimeout(timeoutId)
  }

  const contentType = response.headers.get('content-type') || ''
  const data = contentType.includes('application/json') ? await response.json() : await response.text()

  if (!response.ok) {
    const message = typeof data === 'object' ? data.detail || data.error || JSON.stringify(data) : data
    throw new Error(message || `Request gagal dengan status ${response.status}`)
  }
  return data
}

export function analisisKlasifikasiMerek(payload) {
  return request('/api/trademark/cek/', {
    method: 'POST',
    body: JSON.stringify({ ...payload, asinkron: true }),
  }).then((queued) => waitForBackgroundJob(queued, 'klasifikasi AI'))
}

export function getFiturMerek() {
  return request('/api/trademark/fitur/')
}

export function eskalasiKelasMerek(payload) {
  return request('/api/trademark/cek-kelas/eskalasi/', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function cekKemiripanMerek(payload, logoFile = null) {
  const body = new FormData()
  body.append('nama_merek', payload.nama_merek)
  body.append('deskripsi_produk', payload.deskripsi_produk)
  if (logoFile) body.append('logo_merek', logoFile)
  return request('/api/trademark/cek-kemiripan/', { method: 'POST', body })
}

export function tanyaChatbot(pertanyaan, sesiId) {
  return request('/api/chatbot/tanya/', {
    method: 'POST',
    body: JSON.stringify({ pertanyaan, sesi_id: sesiId, asinkron: true }),
  }).then((queued) => waitForBackgroundJob(queued, 'chatbot'))
}

export function kirimRating(percakapanId, ratingMembantu) {
  return request('/api/chatbot/rating/', {
    method: 'POST',
    body: JSON.stringify({
      percakapan_id: percakapanId,
      rating_membantu: ratingMembantu,
    }),
  })
}

export function getFaq({ q = '', kategori = '' } = {}) {
  const params = new URLSearchParams()
  if (q.trim()) params.set('q', q.trim())
  if (kategori) params.set('kategori', kategori)
  const suffix = params.toString() ? `?${params.toString()}` : ''
  return request(`/api/knowledge/faq/${suffix}`)
}

export function getKategori() {
  return request('/api/knowledge/kategori/')
}

export function getStatusKonsultasi(pelacakanId) {
  return request(`/api/chatbot/status/${encodeURIComponent(pelacakanId)}/`)
}

export function getStatusLayanan() {
  return request('/api/core/health/')
}

export function getStatistikLayanan(days = 7) {
  return request(`/api/core/statistik-layanan/?days=${encodeURIComponent(days)}`)
}

export function kirimUjiCoba(payload) {
  return request('/api/core/uji-coba/', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function unwrapResults(data) {
  return Array.isArray(data) ? data : data?.results || []
}
