import React, { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { useNavigate } from 'react-router-dom';
import PageHeader from '../components/PageHeader';

export default function Settings() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [copied, setCopied] = useState('');

  const copyToClipboard = (text, key) => {
    navigator.clipboard.writeText(text).then(() => {
      setCopied(key);
      setTimeout(() => setCopied(''), 2000);
    });
  };

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8765/api/v1';

  return (
    <div className="space-y-6 max-w-3xl">
      <PageHeader title="Settings" description="Account and system configuration" />

      {/* Account */}
      <div className="card">
        <h2 className="text-sm font-semibold text-white mb-4">Account</h2>
        <div className="space-y-4">
          <div>
            <div className="label">Email</div>
            <div className="text-sm text-gray-300">{user?.email || '—'}</div>
          </div>
          <div>
            <div className="label">User ID</div>
            <div className="flex items-center gap-2">
              <code className="text-xs text-gray-400 font-mono bg-gray-800 px-2 py-1 rounded">{user?.id || '—'}</code>
              {user?.id && (
                <button onClick={() => copyToClipboard(user.id, 'userId')}
                  className="text-xs text-gray-500 hover:text-gray-300 transition-colors">
                  {copied === 'userId' ? '✓ Copied' : 'Copy'}
                </button>
              )}
            </div>
          </div>
          <div>
            <div className="label">Workspace ID</div>
            <div className="flex items-center gap-2">
              <code className="text-xs text-gray-400 font-mono bg-gray-800 px-2 py-1 rounded">{user?.workspace_id || '—'}</code>
              {user?.workspace_id && (
                <button onClick={() => copyToClipboard(user.workspace_id, 'wsId')}
                  className="text-xs text-gray-500 hover:text-gray-300 transition-colors">
                  {copied === 'wsId' ? '✓ Copied' : 'Copy'}
                </button>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* API Access */}
      <div className="card">
        <h2 className="text-sm font-semibold text-white mb-4">API Access</h2>
        <div className="space-y-3">
          <div>
            <div className="label">API Base URL</div>
            <div className="flex items-center gap-2">
              <code className="text-xs text-gray-400 font-mono bg-gray-800 px-2 py-1 rounded flex-1">{API_URL}</code>
              <button onClick={() => copyToClipboard(API_URL, 'apiUrl')}
                className="text-xs text-gray-500 hover:text-gray-300 transition-colors flex-shrink-0">
                {copied === 'apiUrl' ? '✓ Copied' : 'Copy'}
              </button>
            </div>
          </div>
          <div>
            <div className="label">OpenAPI Docs</div>
            <a href={`${API_URL}/docs`} target="_blank" rel="noopener noreferrer"
              className="text-xs text-indigo-400 hover:text-indigo-300 transition-colors">
              {API_URL}/docs →
            </a>
          </div>
          <div>
            <div className="label">Health Check</div>
            <a href={`${API_URL.replace('/api/v1', '')}/health`} target="_blank" rel="noopener noreferrer"
              className="text-xs text-indigo-400 hover:text-indigo-300 transition-colors">
              {API_URL.replace('/api/v1', '')}/health →
            </a>
          </div>
        </div>
      </div>

      {/* Capabilities */}
      <div className="card">
        <h2 className="text-sm font-semibold text-white mb-4">Platform Capabilities</h2>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-2">
          {[
            ['Cost Intelligence', 'Predict and track AI operation costs'],
            ['Intelligent Routing', 'Auto-route to cheapest/best provider'],
            ['Budget Guardrails', 'Hard limits with threshold alerts'],
            ['Tamper-Proof Audit', 'Cryptographically signed operation logs'],
            ['Privacy-by-Design', 'PII detection and auto-redaction'],
            ['Plugin System', 'Extensible via custom plugins'],
            ['Anomaly Detection', 'ML-powered cost spike detection'],
            ['Autonomous Optimization', 'Self-tuning routing and caching'],
            ['Multi-Tenant', 'Workspace isolation per team/client'],
            ['TrapMaster Pro', 'Music production AI assistant'],
            ['ClipCrafter', 'AI-powered video clip generator'],
            ['SCIM / SSO', 'Enterprise identity integration'],
          ].map(([name, desc]) => (
            <div key={name} className="flex items-start gap-2 p-2 rounded-lg">
              <span className="text-emerald-400 mt-0.5 flex-shrink-0">✓</span>
              <div>
                <div className="text-xs font-medium text-gray-300">{name}</div>
                <div className="text-xs text-gray-600">{desc}</div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Danger zone */}
      <div className="card border-red-900/50">
        <h2 className="text-sm font-semibold text-red-400 mb-4">Danger Zone</h2>
        <div className="flex items-center justify-between">
          <div>
            <div className="text-sm text-gray-300">Sign Out</div>
            <div className="text-xs text-gray-500">Clears your session token and returns to login</div>
          </div>
          <button onClick={handleLogout} className="btn-danger text-xs">Sign Out</button>
        </div>
      </div>
    </div>
  );
}
