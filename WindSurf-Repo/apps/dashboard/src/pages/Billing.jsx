import React, { useEffect, useState, useCallback, useRef } from 'react';
import PageHeader from '../components/PageHeader';
import LoadingSpinner from '../components/LoadingSpinner';
import api from '../utils/api';

const API_BASE = process.env.REACT_APP_API_URL || 'http://localhost:8765/api/v1';

// Toast component
function Toast({ message, type, id, onClose }) {
  useEffect(() => {
    const timer = setTimeout(onClose, 4000);
    return () => clearTimeout(timer);
  }, [onClose]);

  const bgColor = type === 'success' ? 'bg-emerald-900/80' : type === 'error' ? 'bg-red-900/80' : 'bg-blue-900/80';
  const borderColor = type === 'success' ? 'border-emerald-700' : type === 'error' ? 'border-red-700' : 'border-blue-700';
  const textColor = type === 'success' ? 'text-emerald-200' : type === 'error' ? 'text-red-200' : 'text-blue-200';
  const icon = type === 'success' ? '✓' : type === 'error' ? '✕' : 'ℹ';

  return (
    <div
      className={`${bgColor} ${borderColor} ${textColor} border rounded-lg px-4 py-3 text-sm flex items-center gap-2 animate-fade-in`}
      style={{
        animation: 'fadeIn 0.3s ease-in-out',
      }}
    >
      <span className="text-base">{icon}</span>
      <span>{message}</span>
      <button onClick={onClose} className="ml-auto text-lg leading-none hover:opacity-70">&times;</button>
    </div>
  );
}

function ToastContainer({ toasts, onClose }) {
  return (
    <div className="fixed bottom-5 right-5 z-50 flex flex-col gap-2 max-w-sm w-full">
      {toasts.map((toast) => (
        <Toast
          key={toast.id}
          {...toast}
          onClose={() => onClose(toast.id)}
        />
      ))}
    </div>
  );
}

const PLANS = [
  {
    id: 'starter',
    name: 'Starter',
    price: 29,
    description: 'Perfect for small projects',
    features: [
      '5 API keys',
      'Up to 100k requests/month',
      'Basic analytics',
      'Community support',
      'Email support',
    ],
  },
  {
    id: 'pro',
    name: 'Pro',
    price: 79,
    description: 'Best for growing teams',
    features: [
      'Unlimited API keys',
      'Up to 1M requests/month',
      'Advanced analytics',
      'Priority email support',
      'Slack integration',
      'Team management',
    ],
    popular: true,
  },
  {
    id: 'enterprise',
    name: 'Enterprise',
    price: 299,
    description: 'For large-scale operations',
    features: [
      'Unlimited everything',
      'Unlimited requests',
      'Custom analytics',
      '24/7 phone support',
      'Dedicated account manager',
      'Custom integrations',
      'SLA guarantee',
    ],
  },
];

export default function Billing() {
  const [subscription, setSubscription] = useState(null);
  const [plans, setPlans] = useState(PLANS);
  const [invoices, setInvoices] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [upgrading, setUpgrading] = useState(null);
  const [toasts, setToasts] = useState([]);
  const pollCountRef = useRef(0);
  const pollTimerRef = useRef(null);

  const addToast = useCallback((message, type = 'info') => {
    const id = Date.now();
    setToasts((prev) => [...prev, { id, message, type }]);
    return id;
  }, []);

  const removeToast = useCallback((id) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  // Load subscription and invoices on mount
  const load = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      const [subRes, invoicesRes] = await Promise.all([
        api.get('/stripe/subscription'),
        api.get('/stripe/invoices'),
      ]);

      setSubscription(subRes.data);
      setInvoices(invoicesRes.data.invoices || []);
    } catch (err) {
      const msg = err.response?.data?.detail || err.message || 'Failed to load billing data';
      setError(msg);
      addToast(msg, 'error');
    } finally {
      setLoading(false);
    }
  }, [addToast]);

  // Poll for session completion
  const pollSessionStatus = useCallback(
    (sessionId) => {
      if (pollCountRef.current >= 20) {
        addToast('Upgrade verification timed out. Please check your billing settings.', 'error');
        return;
      }

      pollCountRef.current += 1;

      const pollFn = async () => {
        try {
          const res = await api.get(`/stripe/session/${sessionId}`);
          if (res.data.status === 'complete') {
            clearInterval(pollTimerRef.current);
            pollCountRef.current = 0;
            addToast('Upgrade successful! Your plan is now active.', 'success');
            await load();
          }
        } catch (err) {
          addToast('Failed to verify upgrade status.', 'error');
          clearInterval(pollTimerRef.current);
          pollCountRef.current = 0;
        }
      };

      pollFn();
    },
    [addToast, load]
  );

  // Check for session_id in URL on mount
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const sessionId = params.get('session_id');

    if (sessionId) {
      addToast('Verifying your payment...', 'info');
      pollCountRef.current = 0;
      pollTimerRef.current = setInterval(() => {
        pollSessionStatus(sessionId);
      }, 3000);

      // Clean URL
      window.history.replaceState({}, document.title, window.location.pathname);

      return () => {
        if (pollTimerRef.current) clearInterval(pollTimerRef.current);
      };
    }
  }, []);

  // Load data
  useEffect(() => {
    load();
  }, [load]);

  // Handle upgrade click
  const handleUpgrade = useCallback(
    async (planId) => {
      try {
        setUpgrading(planId);

        const res = await api.post('/stripe/checkout', {
          plan_id: planId,
          billing_cycle: 'monthly',
        });

        if (res.data.checkout_url) {
          window.location.href = res.data.checkout_url;
        } else {
          addToast('Failed to create checkout session', 'error');
        }
      } catch (err) {
        const msg = err.response?.data?.detail || 'Failed to initiate upgrade';
        addToast(msg, 'error');
      } finally {
        setUpgrading(null);
      }
    },
    [addToast]
  );

  // Handle manage billing
  const handleManageBilling = useCallback(async () => {
    try {
      const res = await api.post('/stripe/portal');
      if (res.data.portal_url) {
        window.open(res.data.portal_url, '_blank');
      } else {
        addToast('Failed to open billing portal', 'error');
      }
    } catch (err) {
      const msg = err.response?.data?.detail || 'Failed to open billing portal';
      addToast(msg, 'error');
    }
  }, [addToast]);

  if (loading) return <LoadingSpinner centered />;

  const currentPlan = subscription?.current_plan?.id || null;
  const status = subscription?.status || 'inactive';
  const nextBillingDate = subscription?.next_billing_date || null;

  return (
    <div className="space-y-6 max-w-7xl">
      <PageHeader
        title="Billing"
        description="Manage your subscription and invoices"
        actions={
          currentPlan && (
            <button onClick={handleManageBilling} className="btn-secondary text-xs">
              💳 Manage Billing
            </button>
          )
        }
      />

      {error && (
        <div className="card bg-red-900/10 border-red-800 text-red-300 text-sm">
          {error}
        </div>
      )}

      {/* Current Plan Status */}
      {currentPlan && (
        <div className="card space-y-4">
          <div>
            <h2 className="text-lg font-semibold text-white mb-1">Current Plan</h2>
            <p className="text-sm text-gray-400">Active subscription details</p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="bg-gray-800/50 rounded-lg p-4 border border-gray-700">
              <div className="text-xs text-gray-400 mb-1">Plan</div>
              <div className="text-xl font-semibold text-white capitalize">
                {PLANS.find((p) => p.id === currentPlan)?.name || currentPlan}
              </div>
              <div className="text-sm text-gray-400 mt-1">
                ${PLANS.find((p) => p.id === currentPlan)?.price || '0'}/mo
              </div>
            </div>

            <div className="bg-gray-800/50 rounded-lg p-4 border border-gray-700">
              <div className="text-xs text-gray-400 mb-1">Status</div>
              <div className="flex items-center gap-2">
                <span className={`w-2 h-2 rounded-full ${status === 'active' ? 'bg-emerald-400' : 'bg-amber-400'}`} />
                <span className="text-lg font-semibold text-white capitalize">{status}</span>
              </div>
            </div>

            <div className="bg-gray-800/50 rounded-lg p-4 border border-gray-700">
              <div className="text-xs text-gray-400 mb-1">Next Billing</div>
              <div className="text-lg font-semibold text-white">
                {nextBillingDate ? new Date(nextBillingDate).toLocaleDateString() : '—'}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Plans Grid */}
      <div>
        <h2 className="text-lg font-semibold text-white mb-4">Plans</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {plans.map((plan) => {
            const isCurrent = plan.id === currentPlan;
            const isLower = currentPlan && PLANS.findIndex((p) => p.id === currentPlan) > PLANS.findIndex((p) => p.id === plan.id);

            return (
              <div
                key={plan.id}
                className={`card relative flex flex-col ${
                  plan.popular ? 'ring-2 ring-indigo-600' : ''
                } ${isCurrent ? 'border-emerald-700' : ''}`}
              >
                {plan.popular && (
                  <div className="absolute -top-3 left-4 bg-indigo-600 text-white px-3 py-1 rounded-full text-xs font-semibold">
                    Popular
                  </div>
                )}

                <div className={isCurrent ? 'bg-emerald-900/20 border border-emerald-700 rounded-lg p-3 mb-4 text-sm text-emerald-200' : ''}>
                  {isCurrent && '✓ Current Plan'}
                </div>

                <h3 className="text-lg font-semibold text-white mb-1">{plan.name}</h3>
                <p className="text-sm text-gray-400 mb-4">{plan.description}</p>

                <div className="mb-6">
                  <div className="text-3xl font-bold text-white">${plan.price}</div>
                  <div className="text-xs text-gray-400">/month, billed monthly</div>
                </div>

                <button
                  onClick={() => handleUpgrade(plan.id)}
                  disabled={isCurrent || isLower || upgrading === plan.id}
                  className={`w-full py-2 px-4 rounded-lg font-medium text-sm transition-colors mb-6 ${
                    isCurrent
                      ? 'bg-gray-800 text-gray-400 cursor-not-allowed'
                      : isLower
                        ? 'bg-gray-800 text-gray-400 cursor-not-allowed'
                        : upgrading === plan.id
                          ? 'bg-indigo-600/50 text-white'
                          : 'bg-indigo-600 hover:bg-indigo-500 text-white'
                  }`}
                >
                  {upgrading === plan.id ? 'Processing...' : isCurrent ? 'Current Plan' : isLower ? 'Downgrade' : 'Upgrade'}
                </button>

                <ul className="space-y-2 flex-1">
                  {plan.features.map((feature, idx) => (
                    <li key={idx} className="text-sm text-gray-300 flex items-start gap-2">
                      <span className="text-emerald-400 font-bold mt-0.5 flex-shrink-0">✓</span>
                      <span>{feature}</span>
                    </li>
                  ))}
                </ul>
              </div>
            );
          })}
        </div>
      </div>

      {/* Invoices */}
      <div className="card space-y-4">
        <div>
          <h2 className="text-lg font-semibold text-white mb-1">Invoice History</h2>
          <p className="text-sm text-gray-400">Download and view past invoices</p>
        </div>

        {invoices.length === 0 ? (
          <div className="py-12 text-center">
            <div className="text-4xl mb-3">📄</div>
            <p className="text-gray-400">No invoices yet</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-800">
                  <th className="text-left py-3 px-4 text-xs font-semibold text-gray-400">Invoice</th>
                  <th className="text-left py-3 px-4 text-xs font-semibold text-gray-400">Date</th>
                  <th className="text-left py-3 px-4 text-xs font-semibold text-gray-400">Amount</th>
                  <th className="text-left py-3 px-4 text-xs font-semibold text-gray-400">Status</th>
                  <th className="text-right py-3 px-4 text-xs font-semibold text-gray-400">Action</th>
                </tr>
              </thead>
              <tbody>
                {invoices.map((invoice) => (
                  <tr key={invoice.id} className="border-b border-gray-800 hover:bg-gray-800/30 transition-colors">
                    <td className="py-3 px-4 text-gray-200 font-mono text-xs">{invoice.number || invoice.id}</td>
                    <td className="py-3 px-4 text-gray-400">
                      {new Date(invoice.date).toLocaleDateString()}
                    </td>
                    <td className="py-3 px-4 text-gray-200 font-medium">
                      ${(invoice.amount / 100).toFixed(2)}
                    </td>
                    <td className="py-3 px-4">
                      <span
                        className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${
                          invoice.status === 'paid'
                            ? 'bg-emerald-900/50 text-emerald-400 border border-emerald-800'
                            : invoice.status === 'pending'
                              ? 'bg-amber-900/50 text-amber-400 border border-amber-800'
                              : 'bg-gray-700/50 text-gray-300 border border-gray-600'
                        }`}
                      >
                        {invoice.status === 'paid' && '✓'}
                        {invoice.status === 'pending' && '⏱'}
                        {invoice.status !== 'paid' && invoice.status !== 'pending' && '—'}
                        <span className="capitalize">{invoice.status}</span>
                      </span>
                    </td>
                    <td className="py-3 px-4 text-right">
                      {invoice.pdf_url && (
                        <a
                          href={invoice.pdf_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-indigo-400 hover:text-indigo-300 text-xs font-medium transition-colors"
                        >
                          Download
                        </a>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* FAQ */}
      <div className="card space-y-4">
        <h2 className="text-lg font-semibold text-white">Frequently Asked Questions</h2>

        <div className="space-y-3">
          <div className="bg-gray-800/30 rounded-lg p-4 border border-gray-700">
            <h4 className="font-medium text-white mb-2">Can I cancel my subscription?</h4>
            <p className="text-sm text-gray-400">Yes, you can cancel anytime from the billing portal. No long-term contracts required.</p>
          </div>

          <div className="bg-gray-800/30 rounded-lg p-4 border border-gray-700">
            <h4 className="font-medium text-white mb-2">Do you offer annual discounts?</h4>
            <p className="text-sm text-gray-400">Contact our sales team for enterprise pricing and annual billing options.</p>
          </div>

          <div className="bg-gray-800/30 rounded-lg p-4 border border-gray-700">
            <h4 className="font-medium text-white mb-2">What happens when I upgrade?</h4>
            <p className="text-sm text-gray-400">Upgrades take effect immediately. You'll be prorated for the difference in your next billing cycle.</p>
          </div>

          <div className="bg-gray-800/30 rounded-lg p-4 border border-gray-700">
            <h4 className="font-medium text-white mb-2">What payment methods do you accept?</h4>
            <p className="text-sm text-gray-400">We accept all major credit cards, bank transfers, and wire transfers for enterprise accounts.</p>
          </div>
        </div>
      </div>

      <ToastContainer toasts={toasts} onClose={removeToast} />

      <style>{`
        @keyframes fadeIn {
          from {
            opacity: 0;
            transform: translateY(10px);
          }
          to {
            opacity: 1;
            transform: translateY(0);
          }
        }
        .animate-fade-in {
          animation: fadeIn 0.3s ease-in-out;
        }
      `}</style>
    </div>
  );
}
