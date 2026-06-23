// 백엔드 REST 호출 래퍼. vite proxy 가 /api → :8000 으로 전달.
const BASE = '/api'

async function parseError(r, fallback) {
  try {
    const body = await r.json()
    return body.detail || fallback
  } catch {
    return fallback
  }
}

export async function uploadForm(file) {
  const fd = new FormData()
  fd.append('file', file)
  const r = await fetch(`${BASE}/forms/upload`, { method: 'POST', body: fd })
  if (!r.ok) throw new Error(await parseError(r, '업로드 실패'))
  return (await r.json()).form
}

export async function generateFields(formId, concept) {
  const r = await fetch(`${BASE}/forms/${formId}/generate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ concept, overrides: {} }),
  })
  if (!r.ok) throw new Error(await parseError(r, '생성 실패'))
  return (await r.json()).result
}

export async function downloadFilled(formId, fields) {
  const r = await fetch(`${BASE}/forms/${formId}/download`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ fields }),
  })
  if (!r.ok) throw new Error(await parseError(r, '다운로드 준비 실패'))
  return await r.json()
}

export function fileUrl(formId) {
  return `${BASE}/forms/${formId}/file`
}

export async function fetchRecent(limit = 8) {
  try {
    const r = await fetch(`${BASE}/documents/recent?limit=${limit}`)
    if (!r.ok) return { items: [], db: false }
    return await r.json()
  } catch {
    return { items: [], db: false }
  }
}
