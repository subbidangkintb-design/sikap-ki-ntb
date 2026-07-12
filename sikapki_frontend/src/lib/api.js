const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000').replace(/\/$/, '')

async function request(path, options = {}) {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: {
      'Content-Type': 'application/json',
      ...(options.headers || {}),
    },
    ...options,
  })

  const contentType = response.headers.get('content-type') || ''
  const data = contentType.includes('application/json') ? await response.json() : await response.text()

  if (!response.ok) {
    const message = typeof data === 'object' ? data.detail || data.error || JSON.stringify(data) : data
    throw new Error(message || `Request gagal dengan status ${response.status}`)
  }
  return data
}

export function cekMerek(payload) {
  return request('/api/trademark/cek/', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function tanyaChatbot(pertanyaan) {
  return request('/api/chatbot/tanya/', {
    method: 'POST',
    body: JSON.stringify({ pertanyaan }),
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

export function getFaq() {
  return request('/api/knowledge/faq/')
}

export function getKategori() {
  return request('/api/knowledge/kategori/')
}

export function unwrapResults(data) {
  return Array.isArray(data) ? data : data?.results || []
}
