import axios from 'axios';

const BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8765/api/v1';

const api = axios.create({
  baseURL: BASE_URL,
  headers: { 'Content-Type': 'application/json' },
  timeout: 30000,
});

// Inject auth token on every request
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('byos_token');
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

// Handle 401 globally - redirect to login
api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      localStorage.removeItem('byos_token');
      localStorage.removeItem('byos_user');
      window.location.href = '/login';
    }
    return Promise.reject(err);
  }
);

// ─── Auth ─────────────────────────────────────────────────────────────────────
export const authApi = {
  login: (email, password) =>
    api.post('/auth/login-json', { email, password }),
  register: (email, password, full_name) =>
    api.post('/auth/register', { email, password, full_name }),
  me: () => api.get('/auth/me'),
};

// ─── Dashboard ────────────────────────────────────────────────────────────────
export const dashboardApi = {
  getStats: () => api.get('/dashboard/stats'),
  getSystemStatus: () => api.get('/dashboard/system-status'),
  getRecentActivity: (limit = 20) => api.get(`/dashboard/recent-activity?limit=${limit}`),
  getCostTrend: (days = 7) => api.get(`/dashboard/cost-trend?days=${days}`),
  getProviderBreakdown: () => api.get('/dashboard/provider-breakdown'),
  getSavingsSummary: () => api.get('/dashboard/savings-summary'),
  getAnomaliesSummary: () => api.get('/dashboard/anomalies-summary'),
  getBudgetStatus: () => api.get('/dashboard/budget-status'),
  getMonitoringMetrics: (timeRange = '1h') =>
    api.get(`/dashboard/monitoring/metrics?time_range=${timeRange}`),
  executeSystemAction: (action) => api.post(`/dashboard/system-controls/${action}`),
};

// ─── Cost Intelligence ────────────────────────────────────────────────────────
export const costApi = {
  predict: (payload) => api.post('/cost/predict', payload),
  getSummary: (days = 30) => api.get(`/cost/summary?days=${days}`),
  getHistory: (limit = 50, offset = 0) =>
    api.get(`/cost/history?limit=${limit}&offset=${offset}`),
  getProviderComparison: (operationType) =>
    api.get(`/cost/providers?operation_type=${operationType}`),
};

// ─── Budget ───────────────────────────────────────────────────────────────────
export const budgetApi = {
  list: () => api.get('/budget'),
  create: (payload) => api.post('/budget', payload),
  update: (id, payload) => api.put(`/budget/${id}`, payload),
  delete: (id) => api.delete(`/budget/${id}`),
  getAlerts: () => api.get('/budget/alerts'),
};

// ─── Audit Logs ───────────────────────────────────────────────────────────────
export const auditApi = {
  getLogs: (params = {}) => {
    const q = new URLSearchParams();
    if (params.operationType) q.set('operation_type', params.operationType);
    if (params.provider) q.set('provider', params.provider);
    if (params.userId) q.set('user_id', params.userId);
    if (params.startDate) q.set('start_date', params.startDate);
    if (params.endDate) q.set('end_date', params.endDate);
    if (params.limit) q.set('limit', params.limit);
    if (params.offset) q.set('offset', params.offset);
    return api.get(`/audit/logs?${q.toString()}`);
  },
  verify: (logId) => api.get(`/audit/verify/${logId}`),
  getComplianceReport: (payload) => api.post('/audit/compliance-report', payload),
};

// ─── Routing ──────────────────────────────────────────────────────────────────
export const routingApi = {
  getPolicy: () => api.get('/routing/policy'),
  setPolicy: (payload) => api.post('/routing/policy', payload),
  test: (payload) => api.post('/routing/test', payload),
  getHistory: (limit = 50) => api.get(`/routing/history?limit=${limit}`),
  getProviders: () => api.get('/routing/providers'),
};

// ─── Plugins ──────────────────────────────────────────────────────────────────
export const pluginsApi = {
  list: () => api.get('/plugins'),
  enable: (name) => api.post(`/plugins/${name}/enable`),
  disable: (name) => api.post(`/plugins/${name}/disable`),
};

// ─── Apps ─────────────────────────────────────────────────────────────────────
export const appsApi = {
  list: () => api.get('/apps'),
  enable: (appId) => api.post(`/workspaces/apps/${appId}/enable`),
  disable: (appId) => api.post(`/workspaces/apps/${appId}/disable`),
};

// ─── Workspaces ───────────────────────────────────────────────────────────────
export const workspacesApi = {
  getCurrent: () => api.get('/workspaces/current'),
  listSecrets: () => api.get('/workspaces/secrets'),
  createSecret: (payload) => api.post('/workspaces/secrets', payload),
  deleteSecret: (key) => api.delete(`/workspaces/secrets/${key}`),
  getRetentionPolicy: () => api.get('/workspaces/retention-policy'),
  setRetentionPolicy: (payload) => api.put('/workspaces/retention-policy', payload),
};

// ─── Insights ─────────────────────────────────────────────────────────────────
export const insightsApi = {
  getSavings: (startDate, endDate) => {
    const q = new URLSearchParams();
    if (startDate) q.set('start_date', startDate);
    if (endDate) q.set('end_date', endDate);
    return api.get(`/insights/savings?${q.toString()}`);
  },
  getProjected: (monthsAhead = 3) =>
    api.get(`/insights/savings/projected?months_ahead=${monthsAhead}`),
  getSuggestions: () => api.get('/suggestions'),
};

// ─── Anomalies ────────────────────────────────────────────────────────────────
export const anomaliesApi = {
  list: (status) => api.get(`/anomalies${status ? `?status=${status}` : ''}`),
  detect: (payload) => api.post('/anomalies/detect', payload),
  updateStatus: (id, payload) => api.patch(`/anomalies/${id}/status`, payload),
};

// ─── Compliance ───────────────────────────────────────────────────────────────
export const complianceApi = {
  getStatus: () => api.get('/compliance/status'),
  getViolations: () => api.get('/compliance/violations'),
  getPolicies: () => api.get('/compliance/policies'),
};

// ─── Privacy ──────────────────────────────────────────────────────────────────
export const privacyApi = {
  scan: (payload) => api.post('/privacy/scan', payload),
  getReport: () => api.get('/privacy/report'),
};

// ─── Health ───────────────────────────────────────────────────────────────────
export const healthApi = {
  check: () => api.get('/health'),
};

export default api;
