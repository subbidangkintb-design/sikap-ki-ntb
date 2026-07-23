const configuredApiUrl = (import.meta.env.VITE_API_BASE_URL || '').trim()
const API_BASE_URL = (
  configuredApiUrl || `${window.location.protocol}//${window.location.hostname}:8000`
).replace(/\/$/, '')
const REQUEST_TIMEOUT_MS = 45_000

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

export function cekMerek(payload, logoFile = null) {
  if (logoFile) {
    const body = new FormData()
    body.append('nama_merek', payload.nama_merek)
    body.append('deskripsi_produk', payload.deskripsi_produk)
    for (const kelas of payload.kelas_nice_dipilih || []) body.append('kelas_nice_dipilih', kelas)
    body.append('logo_merek', logoFile)
    return request('/api/trademark/cek/', { method: 'POST', body })
  }
  const jsonPayload = { ...payload }
  if (!jsonPayload.kelas_nice_dipilih?.length) delete jsonPayload.kelas_nice_dipilih
  return request('/api/trademark/cek/', {
    method: 'POST',
    body: JSON.stringify(jsonPayload),
  })
}

export function tanyaChatbot(pertanyaan, sesiId) {
  return request('/api/chatbot/tanya/', {
    method: 'POST',
    body: JSON.stringify({ pertanyaan, sesi_id: sesiId }),
  })
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
