import api from './api'

// ── Classification Categories ──

export function getCategoryTree() {
  return api.get('/standards/categories/tree').then(res => res.data)
}

export function getCategories(params) {
  return api.get('/standards/categories/', { params }).then(res => res.data)
}

export function getCategory(id) {
  return api.get(`/standards/categories/${id}`).then(res => res.data)
}

export function createCategory(data) {
  return api.post('/standards/categories/', data).then(res => res.data)
}

export function updateCategory(id, data) {
  return api.put(`/standards/categories/${id}`, data).then(res => res.data)
}

export function deleteCategory(id) {
  return api.delete(`/standards/categories/${id}`).then(res => res.data)
}

export function exportCategories() {
  return api.get('/standards/categories/export', { responseType: 'blob' }).then((res) => {
    const url = window.URL.createObjectURL(new Blob([res.data]))
    const link = document.createElement('a')
    link.href = url
    link.setAttribute('download', 'classification_categories.xlsx')
    document.body.appendChild(link)
    link.click()
    link.remove()
    window.URL.revokeObjectURL(url)
  })
}

export function importCategories(file) {
  const formData = new FormData()
  formData.append('file', file)
  return api.post('/standards/categories/import', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  }).then(res => res.data)
}

// ── Tiering Rules ──

export function getTiers(params) {
  return api.get('/standards/tiers/', { params }).then(res => res.data)
}

export function getTier(id) {
  return api.get(`/standards/tiers/${id}`).then(res => res.data)
}

export function createTier(data) {
  return api.post('/standards/tiers/', data).then(res => res.data)
}

export function updateTier(id, data) {
  return api.put(`/standards/tiers/${id}`, data).then(res => res.data)
}

export function deleteTier(id) {
  return api.delete(`/standards/tiers/${id}`).then(res => res.data)
}

export function exportTiers() {
  return api.get('/standards/tiers/export', { responseType: 'blob' }).then((res) => {
    const url = window.URL.createObjectURL(new Blob([res.data]))
    const link = document.createElement('a')
    link.href = url
    link.setAttribute('download', 'tiering_rules.xlsx')
    document.body.appendChild(link)
    link.click()
    link.remove()
    window.URL.revokeObjectURL(url)
  })
}

export function importTiers(file) {
  const formData = new FormData()
  formData.append('file', file)
  return api.post('/standards/tiers/import', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  }).then(res => res.data)
}
