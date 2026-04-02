import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

export default function Register() {
  const { register, loading } = useAuth();
  const navigate = useNavigate();
  const [form, setForm] = useState({ email: '', password: '', fullName: '' });
  const [error, setError] = useState('');

  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }));

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    if (form.password.length < 8) {
      setError('Password must be at least 8 characters');
      return;
    }
    const result = await register(form.email, form.password, form.fullName);
    if (result.success) {
      navigate('/');
    } else {
      setError(result.error || 'Registration failed');
    }
  };

  return (
    <div className="min-h-screen bg-gray-950 flex items-center justify-center p-4">
      <div className="w-full max-w-sm">
        <div className="text-center mb-8">
          <div className="inline-flex w-12 h-12 rounded-xl bg-indigo-600 items-center justify-center text-2xl font-bold text-white mb-4">B</div>
          <h1 className="text-2xl font-bold text-white">Create Account</h1>
          <p className="text-sm text-gray-500 mt-1">Set up your BYOS workspace</p>
        </div>

        <form onSubmit={handleSubmit} className="card space-y-4">
          {error && (
            <div className="p-3 bg-red-900/30 border border-red-800 rounded-lg text-sm text-red-400">
              {error}
            </div>
          )}

          <div>
            <label className="label">Full Name</label>
            <input type="text" className="input" placeholder="Jane Smith"
              value={form.fullName} onChange={set('fullName')} />
          </div>
          <div>
            <label className="label">Email</label>
            <input type="email" className="input" placeholder="you@company.com"
              value={form.email} onChange={set('email')} required autoFocus />
          </div>
          <div>
            <label className="label">Password</label>
            <input type="password" className="input" placeholder="Min. 8 characters"
              value={form.password} onChange={set('password')} required />
          </div>

          <button type="submit" className="btn-primary w-full justify-center py-2.5" disabled={loading}>
            {loading ? (
              <span className="flex items-center gap-2">
                <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                Creating…
              </span>
            ) : 'Create Account'}
          </button>

          <p className="text-center text-xs text-gray-500">
            Have an account?{' '}
            <Link to="/login" className="text-indigo-400 hover:text-indigo-300 transition-colors">
              Sign in
            </Link>
          </p>
        </form>
      </div>
    </div>
  );
}
