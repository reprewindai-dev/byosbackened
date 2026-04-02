# Stripe Billing Page - Code Reference

## Quick Implementation Reference

### Key Imports
```javascript
import React, { useEffect, useState, useCallback, useRef } from 'react';
import PageHeader from '../components/PageHeader';
import LoadingSpinner from '../components/LoadingSpinner';
import api from '../utils/api';
```

### Plan Configuration
```javascript
const PLANS = [
  {
    id: 'starter',
    name: 'Starter',
    price: 29,
    description: 'Perfect for small projects',
    features: ['5 API keys', 'Up to 100k requests/month', ...],
  },
  {
    id: 'pro',
    name: 'Pro',
    price: 79,
    description: 'Best for growing teams',
    features: [...],
    popular: true, // Shows "Popular" badge
  },
  {
    id: 'enterprise',
    name: 'Enterprise',
    price: 299,
    description: 'For large-scale operations',
    features: [...],
  },
];
```

### Toast Notification System
```javascript
// Add toast
const id = addToast('Payment successful!', 'success');

// Remove toast
removeToast(id);

// Toast types: 'success' (green), 'error' (red), 'info' (blue)
```

### API Calls

#### Load Data
```javascript
const [subscription, setSubscription] = useState(null);
const [invoices, setInvoices] = useState([]);
const [loading, setLoading] = useState(true);

const load = useCallback(async () => {
  try {
    const [subRes, invoicesRes] = await Promise.all([
      api.get('/stripe/subscription'),
      api.get('/stripe/invoices'),
    ]);
    setSubscription(subRes.data);
    setInvoices(invoicesRes.data.invoices || []);
  } catch (err) {
    addToast(err.response?.data?.detail || 'Error', 'error');
  } finally {
    setLoading(false);
  }
}, []);
```

#### Initiate Checkout
```javascript
const handleUpgrade = useCallback(async (planId) => {
  try {
    setUpgrading(planId);
    const res = await api.post('/stripe/checkout', {
      plan_id: planId,
      billing_cycle: 'monthly',
    });
    window.location.href = res.data.checkout_url;
  } catch (err) {
    addToast(err.response?.data?.detail || 'Failed', 'error');
  } finally {
    setUpgrading(null);
  }
}, [addToast]);
```

#### Poll Session Status
```javascript
useEffect(() => {
  const params = new URLSearchParams(window.location.search);
  const sessionId = params.get('session_id');
  
  if (sessionId) {
    addToast('Verifying your payment...', 'info');
    pollCountRef.current = 0;
    pollTimerRef.current = setInterval(() => {
      pollSessionStatus(sessionId);
    }, 3000); // Poll every 3 seconds
    
    window.history.replaceState({}, document.title, window.location.pathname);
    
    return () => {
      if (pollTimerRef.current) clearInterval(pollTimerRef.current);
    };
  }
}, []);
```

#### Open Billing Portal
```javascript
const handleManageBilling = useCallback(async () => {
  try {
    const res = await api.post('/stripe/portal');
    window.open(res.data.portal_url, '_blank');
  } catch (err) {
    addToast(err.response?.data?.detail || 'Failed', 'error');
  }
}, [addToast]);
```

### JSX Components

#### Current Plan Display
```jsx
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
          {PLANS.find((p) => p.id === currentPlan)?.name}
        </div>
        <div className="text-sm text-gray-400 mt-1">
          ${PLANS.find((p) => p.id === currentPlan)?.price}/mo
        </div>
      </div>
      {/* Status and Next Billing */}
    </div>
  </div>
)}
```

#### Plan Cards Grid
```jsx
<div className="grid grid-cols-1 md:grid-cols-3 gap-4">
  {plans.map((plan) => {
    const isCurrent = plan.id === currentPlan;
    const isLower = currentPlan && 
      PLANS.findIndex((p) => p.id === currentPlan) > 
      PLANS.findIndex((p) => p.id === plan.id);

    return (
      <div key={plan.id} className={`card relative flex flex-col ${
        plan.popular ? 'ring-2 ring-indigo-600' : ''
      } ${isCurrent ? 'border-emerald-700' : ''}`}>
        {plan.popular && (
          <div className="absolute -top-3 left-4 bg-indigo-600 text-white px-3 py-1 rounded-full text-xs font-semibold">
            Popular
          </div>
        )}

        {isCurrent && (
          <div className="bg-emerald-900/20 border border-emerald-700 rounded-lg p-3 mb-4 text-sm text-emerald-200">
            ✓ Current Plan
          </div>
        )}

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
          {upgrading === plan.id ? 'Processing...' : 
           isCurrent ? 'Current Plan' : 
           isLower ? 'Downgrade' : 'Upgrade'}
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
```

#### Invoice Table
```jsx
<div className="card space-y-4">
  <div>
    <h2 className="text-lg font-semibold text-white mb-1">Invoice History</h2>
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
              <td className="py-3 px-4 text-gray-200 font-mono text-xs">
                {invoice.number || invoice.id}
              </td>
              <td className="py-3 px-4 text-gray-400">
                {new Date(invoice.date).toLocaleDateString()}
              </td>
              <td className="py-3 px-4 text-gray-200 font-medium">
                ${(invoice.amount / 100).toFixed(2)}
              </td>
              <td className="py-3 px-4">
                <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${
                  invoice.status === 'paid'
                    ? 'bg-emerald-900/50 text-emerald-400 border border-emerald-800'
                    : invoice.status === 'pending'
                      ? 'bg-amber-900/50 text-amber-400 border border-amber-800'
                      : 'bg-gray-700/50 text-gray-300 border border-gray-600'
                }`}>
                  {invoice.status === 'paid' && '✓'}
                  {invoice.status === 'pending' && '⏱'}
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
```

#### Toast Component
```jsx
function Toast({ message, type, id, onClose }) {
  useEffect(() => {
    const timer = setTimeout(onClose, 4000);
    return () => clearTimeout(timer);
  }, [onClose]);

  const bgColor = type === 'success' ? 'bg-emerald-900/80' : 
                  type === 'error' ? 'bg-red-900/80' : 'bg-blue-900/80';
  const borderColor = type === 'success' ? 'border-emerald-700' : 
                      type === 'error' ? 'border-red-700' : 'border-blue-700';
  const textColor = type === 'success' ? 'text-emerald-200' : 
                    type === 'error' ? 'text-red-200' : 'text-blue-200';
  const icon = type === 'success' ? '✓' : type === 'error' ? '✕' : 'ℹ';

  return (
    <div className={`${bgColor} ${borderColor} ${textColor} border rounded-lg px-4 py-3 text-sm flex items-center gap-2 animate-fade-in`}>
      <span className="text-base">{icon}</span>
      <span>{message}</span>
      <button onClick={onClose} className="ml-auto text-lg leading-none hover:opacity-70">
        &times;
      </button>
    </div>
  );
}

function ToastContainer({ toasts, onClose }) {
  return (
    <div className="fixed bottom-5 right-5 z-50 flex flex-col gap-2 max-w-sm w-full">
      {toasts.map((toast) => (
        <Toast key={toast.id} {...toast} onClose={() => onClose(toast.id)} />
      ))}
    </div>
  );
}
```

### State Hook Setup
```javascript
const [subscription, setSubscription] = useState(null);
const [plans, setPlans] = useState(PLANS);
const [invoices, setInvoices] = useState([]);
const [loading, setLoading] = useState(true);
const [error, setError] = useState(null);
const [upgrading, setUpgrading] = useState(null);
const [toasts, setToasts] = useState([]);
const pollCountRef = useRef(0);
const pollTimerRef = useRef(null);
```

### CSS Animation
```css
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
```

## Integration Checklist

### 1. Copy Component
- Copy `/apps/dashboard/src/pages/Billing.jsx` to your project

### 2. Update Routes
In `App.js`:
```javascript
import Billing from './pages/Billing';

// Add route:
<Route path="/billing" element={<ProtectedRoute><Billing /></ProtectedRoute>} />
```

### 3. Update Navigation
In `Layout.jsx`, add to NAV array:
```javascript
{ to: '/billing', icon: '💳', label: 'Billing' }
```

### 4. Implement Backend Endpoints
All 6 endpoints in `/api/v1/stripe/`:
- `GET /subscription`
- `GET /plans`
- `POST /checkout`
- `GET /session/{id}`
- `POST /portal`
- `GET /invoices`

### 5. Configure Environment
Set `REACT_APP_API_URL` in `.env`

### 6. Test Flow
1. Load `/billing` page
2. Click upgrade button
3. Complete Stripe test payment
4. Verify polling and success notification
5. Check invoice list displays

## Common Customizations

### Change Plan Pricing
Edit `PLANS` constant at top of Billing.jsx

### Modify Plan Features
Update `features` array for each plan

### Change Poll Interval
In `useEffect`, change `3000` to desired milliseconds

### Change Max Poll Attempts
Change `20` in `if (pollCountRef.current >= 20)`

### Customize Toast Styling
Edit `Toast` component CSS classes

### Change Button Text
Edit the button label logic in plan cards

### Adjust Grid Layout
Change `grid-cols-1 md:grid-cols-3` to different breakpoints

## Performance Tips

1. Memoize plan comparison functions
2. Use React.memo for plan cards if list grows large
3. Implement virtual scrolling for invoices if list is huge (100+)
4. Consider pagination for invoices
5. Cache subscription data with React Query or SWR for production

## Security Notes

1. Never expose Stripe secret key in frontend
2. Token handling is done by axios interceptor automatically
3. Stripe checkout URL must be HTTPS only
4. Validate plan IDs against whitelist before sending to API
5. Never trust invoice amounts from frontend

---

**Last Updated**: 2026-02-24
**Status**: Production-Ready
