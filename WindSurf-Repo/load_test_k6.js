import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate } from 'k6/metrics';

// Custom metrics
const errorRate = new Rate('errors');

// Test configuration
export const options = {
  stages: [
    { duration: '2m', target: 100 }, // Ramp up to 100 users
    { duration: '5m', target: 100 }, // Stay at 100 users
    { duration: '2m', target: 500 }, // Ramp up to 500 users  
    { duration: '5m', target: 500 }, // Stay at 500 users
    { duration: '2m', target: 1000 }, // Ramp up to 1000 users
    { duration: '5m', target: 1000 }, // Stay at 1000 users
    { duration: '2m', target: 0 }, // Ramp down
  ],
  thresholds: {
    http_req_duration: ['p(95)<100'], // 95% of requests under 100ms
    http_req_failed: ['rate<0.01'], // Error rate under 1%
    errors: ['rate<0.01'], // Custom error rate under 1%
  },
};

const BASE_URL = 'http://localhost:8000';

export function setup() {
  // Login to get token
  const loginResponse = http.post(`${BASE_URL}/api/v1/auth/login-json`, {
    username: 'admin',
    password: 'admin123'
  });
  
  check(loginResponse, {
    'login successful': (r) => r.status === 200,
    'token received': (r) => r.json('access_token') !== undefined,
  });
  
  return {
    token: loginResponse.json('access_token')
  };
}

export default function(data) {
  const headers = {
    'Authorization': `Bearer ${data.token}`,
    'Content-Type': 'application/json'
  };

  // Test 1: Health endpoint
  let healthResponse = http.get(`${BASE_URL}/health`, { headers });
  let healthOk = check(healthResponse, {
    'health status is 200': (r) => r.status === 200,
    'health response time < 50ms': (r) => r.timings.duration < 50,
  });
  errorRate.add(!healthOk);

  // Test 2: Dashboard config
  let configResponse = http.get(`${BASE_URL}/api/v1/admin/dashboard/config`, { headers });
  let configOk = check(configResponse, {
    'config status is 200': (r) => r.status === 200,
    'config response time < 200ms': (r) => r.timings.duration < 200,
  });
  errorRate.add(!configOk);

  // Test 3: Plans API
  let plansResponse = http.get(`${BASE_URL}/api/plans`, { headers });
  let plansOk = check(plansResponse, {
    'plans status is 200': (r) => r.status === 200,
    'plans response time < 100ms': (r) => r.timings.duration < 100,
  });
  errorRate.add(!plansOk);

  // Test 4: System status
  let statusResponse = http.get(`${BASE_URL}/api/v1/admin/dashboard/system-status`, { headers });
  let statusOk = check(statusResponse, {
    'status status is 200': (r) => r.status === 200,
    'status response time < 150ms': (r) => r.timings.duration < 150,
  });
  errorRate.add(!statusOk);

  // Test 5: Metrics
  let metricsResponse = http.get(`${BASE_URL}/api/v1/admin/dashboard/metrics`, { headers });
  let metricsOk = check(metricsResponse, {
    'metrics status is 200': (r) => r.status === 200,
    'metrics response time < 150ms': (r) => r.timings.duration < 150,
  });
  errorRate.add(!metricsOk);

  sleep(1);
}

export function teardown(data) {
  // Cleanup if needed
  console.log('Load test completed');
}
