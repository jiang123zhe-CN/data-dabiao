import api from './api'

export function getComplianceSummary() {
  return api.get('/reports/compliance/summary').then(res => res.data)
}

export function getComplianceCategoryTier() {
  return api.get('/reports/compliance/by-category-tier').then(res => res.data)
}

export function getComplianceAuditTrail(params) {
  return api.get('/reports/compliance/audit-trail', { params }).then(res => res.data)
}

export function getComplianceTaggingHistory(params) {
  return api.get('/reports/compliance/tagging-history', { params }).then(res => res.data)
}

export function getComplianceGaps() {
  return api.get('/reports/compliance/gaps').then(res => res.data)
}

export function exportComplianceReport() {
  return api.get('/reports/compliance/export', { responseType: 'blob' }).then((res) => {
    const url = window.URL.createObjectURL(new Blob([res.data]))
    const link = document.createElement('a')
    link.href = url
    link.setAttribute('download', 'compliance_report.xlsx')
    document.body.appendChild(link)
    link.click()
    link.remove()
    window.URL.revokeObjectURL(url)
  })
}
