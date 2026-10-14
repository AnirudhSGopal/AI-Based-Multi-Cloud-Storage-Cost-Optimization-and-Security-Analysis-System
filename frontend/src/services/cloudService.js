import api from './api'

const cloudService = {
  getAccounts: () => api.get('/api/v1/cloud/accounts'),
  createAccount: (data) => api.post('/api/v1/cloud/accounts', data),
  testConnection: (data) => api.post('/api/v1/cloud/accounts/test', data),
  syncAccount: (id) => api.get(`/api/v1/cloud/accounts/${id}`),
  deleteAccount: (id) => api.delete(`/api/v1/cloud/accounts/${id}`),
  getChartTrend: () => api.get('/api/v1/cloud/chart-data'),
}

export default cloudService
