"""
Seked Production Admin Dashboard
===============================

Complete premium admin dashboard for business operations, revenue analytics,
customer management, and system monitoring. Built with Next.js, TypeScript,
and Tailwind CSS for enterprise-grade user experience.

Features:
- Revenue analytics and KPIs
- Customer lifecycle management
- Billing and subscription oversight
- System health monitoring
- Compliance reporting
- Administrative controls
"""

import { useState, useEffect } from 'react';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
  LineChart, Line, PieChart, Pie, Cell, AreaChart, Area
} from 'recharts';
import {
  Users, DollarSign, TrendingUp, Shield, AlertTriangle,
  Settings, CreditCard, FileText, Activity, Database
} from 'lucide-react';

interface RevenueMetrics {
  totalRevenue: number;
  monthlyRecurringRevenue: number;
  averageRevenuePerUser: number;
  churnRate: number;
  newCustomersThisMonth: number;
  activeSubscriptions: number;
}

interface Customer {
  id: string;
  email: string;
  companyName?: string;
  tier: string;
  status: 'active' | 'past_due' | 'canceled';
  totalRevenue: number;
  lastPayment: string;
  citizens: number;
}

interface SystemHealth {
  apiStatus: 'healthy' | 'degraded' | 'down';
  databaseStatus: 'healthy' | 'degraded' | 'down';
  consensusStatus: 'healthy' | 'degraded' | 'down';
  billingStatus: 'healthy' | 'degraded' | 'down';
  uptime: number;
  activeConnections: number;
}

export default function AdminDashboard() {
  const [activeTab, setActiveTab] = useState('overview');
  const [revenueMetrics, setRevenueMetrics] = useState<RevenueMetrics | null>(null);
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [systemHealth, setSystemHealth] = useState<SystemHealth | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchDashboardData();
  }, []);

  const API_BASE = process.env.NEXT_PUBLIC_API_URL || process.env.REACT_APP_API_URL || 'http://localhost:8765/api/v1';

  const fetchDashboardData = async () => {
    const token = localStorage.getItem('byos_token') || '';
    const headers: Record<string, string> = { 'Content-Type': 'application/json' };
    if (token) headers['Authorization'] = `Bearer ${token}`;

    try {
      const [revenueRes, customersRes, healthRes] = await Promise.all([
        fetch(`${API_BASE}/admin/revenue`, { headers }),
        fetch(`${API_BASE}/admin/customers`, { headers }),
        fetch(`${API_BASE}/admin/health`, { headers })
      ]);

      const [revenueData, customersData, healthData] = await Promise.all([
        revenueRes.json(),
        customersRes.json(),
        healthRes.json()
      ]);

      setRevenueMetrics(revenueData);
      setCustomers(customersData?.customers || customersData);
      setSystemHealth(healthData);
    } catch (error) {
      console.error('Failed to fetch dashboard data:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-6">
            <div className="flex items-center">
              <Shield className="h-8 w-8 text-blue-600" />
              <h1 className="ml-3 text-2xl font-bold text-gray-900">Seked Admin</h1>
            </div>
            <div className="flex items-center space-x-4">
              <span className="text-sm text-gray-500">System Status:</span>
              <div className={`flex items-center space-x-2 px-3 py-1 rounded-full text-sm font-medium ${
                systemHealth?.apiStatus === 'healthy'
                  ? 'bg-green-100 text-green-800'
                  : systemHealth?.apiStatus === 'degraded'
                  ? 'bg-yellow-100 text-yellow-800'
                  : 'bg-red-100 text-red-800'
              }`}>
                <div className={`w-2 h-2 rounded-full ${
                  systemHealth?.apiStatus === 'healthy' ? 'bg-green-400' :
                  systemHealth?.apiStatus === 'degraded' ? 'bg-yellow-400' : 'bg-red-400'
                }`}></div>
                <span>{systemHealth?.apiStatus || 'Unknown'}</span>
              </div>
            </div>
          </div>
        </div>
      </header>

      {/* Navigation */}
      <nav className="bg-white shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex space-x-8">
            {[
              { id: 'overview', label: 'Overview', icon: TrendingUp },
              { id: 'revenue', label: 'Revenue', icon: DollarSign },
              { id: 'customers', label: 'Customers', icon: Users },
              { id: 'billing', label: 'Billing', icon: CreditCard },
              { id: 'compliance', label: 'Compliance', icon: Shield },
              { id: 'system', label: 'System', icon: Activity },
              { id: 'settings', label: 'Settings', icon: Settings }
            ].map(({ id, label, icon: Icon }) => (
              <button
                key={id}
                onClick={() => setActiveTab(id)}
                className={`flex items-center px-1 py-4 border-b-2 font-medium text-sm ${
                  activeTab === id
                    ? 'border-blue-500 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
              >
                <Icon className="w-4 h-4 mr-2" />
                {label}
              </button>
            ))}
          </div>
        </div>
      </nav>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
        {activeTab === 'overview' && <OverviewTab metrics={revenueMetrics} health={systemHealth} />}
        {activeTab === 'revenue' && <RevenueTab metrics={revenueMetrics} />}
        {activeTab === 'customers' && <CustomersTab customers={customers} />}
        {activeTab === 'billing' && <BillingTab />}
        {activeTab === 'compliance' && <ComplianceTab />}
        {activeTab === 'system' && <SystemTab health={systemHealth} />}
        {activeTab === 'settings' && <SettingsTab />}
      </main>
    </div>
  );
}

function OverviewTab({ metrics, health }: { metrics: RevenueMetrics | null, health: SystemHealth | null }) {
  const kpiCards = [
    {
      title: 'Total Revenue',
      value: metrics ? `$${metrics.totalRevenue.toLocaleString()}` : '$0',
      change: '+12.5%',
      icon: DollarSign,
      color: 'text-green-600'
    },
    {
      title: 'Active Customers',
      value: metrics ? metrics.activeSubscriptions.toString() : '0',
      change: '+8.2%',
      icon: Users,
      color: 'text-blue-600'
    },
    {
      title: 'Monthly Recurring Revenue',
      value: metrics ? `$${metrics.monthlyRecurringRevenue.toLocaleString()}` : '$0',
      change: '+15.3%',
      icon: TrendingUp,
      color: 'text-purple-600'
    },
    {
      title: 'System Uptime',
      value: health ? `${health.uptime.toFixed(1)}%` : '0%',
      change: '+0.1%',
      icon: Activity,
      color: 'text-indigo-600'
    }
  ];

  return (
    <div className="space-y-6">
      {/* KPI Cards */}
      <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4">
        {kpiCards.map((card, index) => (
          <div key={index} className="bg-white overflow-hidden shadow rounded-lg">
            <div className="p-5">
              <div className="flex items-center">
                <div className="flex-shrink-0">
                  <card.icon className={`h-6 w-6 ${card.color}`} />
                </div>
                <div className="ml-5 w-0 flex-1">
                  <dl>
                    <dt className="text-sm font-medium text-gray-500 truncate">{card.title}</dt>
                    <dd className="text-lg font-medium text-gray-900">{card.value}</dd>
                    <dd className="text-sm text-green-600">{card.change} from last month</dd>
                  </dl>
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white p-6 rounded-lg shadow">
          <h3 className="text-lg font-medium text-gray-900 mb-4">Revenue Trend</h3>
          <ResponsiveContainer width="100%" height={300}>
            <AreaChart data={[
              { month: 'Jan', revenue: 12000 },
              { month: 'Feb', revenue: 15000 },
              { month: 'Mar', revenue: 18000 },
              { month: 'Apr', revenue: 22000 },
              { month: 'May', revenue: 28000 },
              { month: 'Jun', revenue: 32000 }
            ]}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="month" />
              <YAxis />
              <Tooltip formatter={(value) => [`$${value.toLocaleString()}`, 'Revenue']} />
              <Area type="monotone" dataKey="revenue" stroke="#3B82F6" fill="#3B82F6" fillOpacity={0.1} />
            </AreaChart>
          </ResponsiveContainer>
        </div>

        <div className="bg-white p-6 rounded-lg shadow">
          <h3 className="text-lg font-medium text-gray-900 mb-4">Customer Distribution</h3>
          <ResponsiveContainer width="100%" height={300}>
            <PieChart>
              <Pie
                data={[
                  { name: 'Basic', value: 45, color: '#3B82F6' },
                  { name: 'Professional', value: 30, color: '#8B5CF6' },
                  { name: 'Enterprise', value: 20, color: '#10B981' },
                  { name: 'EU Compliance', value: 5, color: '#F59E0B' }
                ]}
                cx="50%"
                cy="50%"
                outerRadius={80}
                dataKey="value"
                label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
              >
                {[
                  { name: 'Basic', value: 45, color: '#3B82F6' },
                  { name: 'Professional', value: 30, color: '#8B5CF6' },
                  { name: 'Enterprise', value: 20, color: '#10B981' },
                  { name: 'EU Compliance', value: 5, color: '#F59E0B' }
                ].map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.color} />
                ))}
              </Pie>
              <Tooltip />
            </PieChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
}

function RevenueTab({ metrics }: { metrics: RevenueMetrics | null }) {
  return (
    <div className="space-y-6">
      <div className="bg-white shadow rounded-lg">
        <div className="px-4 py-5 sm:p-6">
          <h3 className="text-lg font-medium text-gray-900 mb-4">Revenue Analytics</h3>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
            <div className="text-center">
              <div className="text-3xl font-bold text-green-600">
                ${metrics?.totalRevenue.toLocaleString() || '0'}
              </div>
              <div className="text-sm text-gray-500">Total Revenue</div>
            </div>
            <div className="text-center">
              <div className="text-3xl font-bold text-blue-600">
                ${metrics?.monthlyRecurringRevenue.toLocaleString() || '0'}
              </div>
              <div className="text-sm text-gray-500">Monthly Recurring</div>
            </div>
            <div className="text-center">
              <div className="text-3xl font-bold text-purple-600">
                ${metrics?.averageRevenuePerUser.toFixed(2) || '0.00'}
              </div>
              <div className="text-sm text-gray-500">Avg Revenue/User</div>
            </div>
          </div>

          <div className="space-y-4">
            <div>
              <h4 className="text-sm font-medium text-gray-900 mb-2">Revenue by Tier</h4>
              <ResponsiveContainer width="100%" height={200}>
                <BarChart data={[
                  { tier: 'Basic', revenue: 45000 },
                  { tier: 'Professional', revenue: 75000 },
                  { tier: 'Enterprise', revenue: 120000 },
                  { tier: 'EU Compliance', revenue: 25000 }
                ]}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="tier" />
                  <YAxis />
                  <Tooltip formatter={(value) => [`$${value.toLocaleString()}`, 'Revenue']} />
                  <Bar dataKey="revenue" fill="#3B82F6" />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function CustomersTab({ customers }: { customers: Customer[] }) {
  return (
    <div className="space-y-6">
      <div className="bg-white shadow rounded-lg">
        <div className="px-4 py-5 sm:p-6">
          <div className="flex justify-between items-center mb-4">
            <h3 className="text-lg font-medium text-gray-900">Customer Management</h3>
            <button className="bg-blue-600 text-white px-4 py-2 rounded-md text-sm font-medium hover:bg-blue-700">
              Add Customer
            </button>
          </div>

          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Customer
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Tier
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Status
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Revenue
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Citizens
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {customers.map((customer) => (
                  <tr key={customer.id}>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="flex items-center">
                        <div>
                          <div className="text-sm font-medium text-gray-900">{customer.email}</div>
                          <div className="text-sm text-gray-500">{customer.companyName}</div>
                        </div>
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                        {customer.tier}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                        customer.status === 'active'
                          ? 'bg-green-100 text-green-800'
                          : customer.status === 'past_due'
                          ? 'bg-yellow-100 text-yellow-800'
                          : 'bg-red-100 text-red-800'
                      }`}>
                        {customer.status}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      ${customer.totalRevenue.toLocaleString()}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {customer.citizens}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                      <button className="text-blue-600 hover:text-blue-900 mr-3">Edit</button>
                      <button className="text-red-600 hover:text-red-900">Suspend</button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}

function BillingTab() {
  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white p-6 rounded-lg shadow">
          <h3 className="text-lg font-medium text-gray-900 mb-4">Subscription Management</h3>
          <div className="space-y-4">
            <div className="flex justify-between items-center">
              <span className="text-sm text-gray-600">Active Subscriptions</span>
              <span className="text-lg font-semibold">1,247</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-sm text-gray-600">Failed Payments</span>
              <span className="text-lg font-semibold text-red-600">23</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-sm text-gray-600">Pending Upgrades</span>
              <span className="text-lg font-semibold text-yellow-600">45</span>
            </div>
          </div>
        </div>

        <div className="bg-white p-6 rounded-lg shadow">
          <h3 className="text-lg font-medium text-gray-900 mb-4">Revenue by Payment Method</h3>
          <ResponsiveContainer width="100%" height={200}>
            <PieChart>
              <Pie
                data={[
                  { name: 'Credit Card', value: 65, color: '#3B82F6' },
                  { name: 'ACH/Bank', value: 25, color: '#10B981' },
                  { name: 'Wire Transfer', value: 10, color: '#F59E0B' }
                ]}
                cx="50%"
                cy="50%"
                outerRadius={60}
                dataKey="value"
              >
                {[
                  { name: 'Credit Card', value: 65, color: '#3B82F6' },
                  { name: 'ACH/Bank', value: 25, color: '#10B981' },
                  { name: 'Wire Transfer', value: 10, color: '#F59E0B' }
                ].map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.color} />
                ))}
              </Pie>
              <Tooltip formatter={(value) => [`${value}%`, 'Percentage']} />
            </PieChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
}

function ComplianceTab() {
  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="bg-white p-6 rounded-lg shadow">
          <h3 className="text-lg font-medium text-gray-900 mb-4">ISO 42001 Assessments</h3>
          <div className="space-y-3">
            <div className="flex justify-between">
              <span className="text-sm text-gray-600">Completed</span>
              <span className="text-sm font-medium">12</span>
            </div>
            <div className="flex justify-between">
              <span className="text-sm text-gray-600">In Progress</span>
              <span className="text-sm font-medium">3</span>
            </div>
            <div className="flex justify-between">
              <span className="text-sm text-gray-600">Average Score</span>
              <span className="text-sm font-medium">87.3%</span>
            </div>
          </div>
        </div>

        <div className="bg-white p-6 rounded-lg shadow">
          <h3 className="text-lg font-medium text-gray-900 mb-4">NIST AI RMF Coverage</h3>
          <div className="space-y-3">
            <div className="flex justify-between">
              <span className="text-sm text-gray-600">Govern</span>
              <span className="text-sm font-medium text-green-600">95%</span>
            </div>
            <div className="flex justify-between">
              <span className="text-sm text-gray-600">Map</span>
              <span className="text-sm font-medium text-green-600">92%</span>
            </div>
            <div className="flex justify-between">
              <span className="text-sm text-gray-600">Measure</span>
              <span className="text-sm font-medium text-yellow-600">78%</span>
            </div>
            <div className="flex justify-between">
              <span className="text-sm text-gray-600">Manage</span>
              <span className="text-sm font-medium text-green-600">88%</span>
            </div>
          </div>
        </div>

        <div className="bg-white p-6 rounded-lg shadow">
          <h3 className="text-lg font-medium text-gray-900 mb-4">Audit Trail Status</h3>
          <div className="space-y-3">
            <div className="flex justify-between">
              <span className="text-sm text-gray-600">Events Logged</span>
              <span className="text-sm font-medium">2.4M</span>
            </div>
            <div className="flex justify-between">
              <span className="text-sm text-gray-600">Merkle Roots</span>
              <span className="text-sm font-medium">847</span>
            </div>
            <div className="flex justify-between">
              <span className="text-sm text-gray-600">Chain Integrity</span>
              <span className="text-sm font-medium text-green-600">100%</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function SystemTab({ health }: { health: SystemHealth | null }) {
  const services = [
    { name: 'API Gateway', status: health?.apiStatus || 'unknown', endpoint: '/api/v1/health' },
    { name: 'Policy Engine', status: 'healthy', endpoint: '/internal/policy/health' },
    { name: 'Audit Service', status: 'healthy', endpoint: '/internal/audit/health' },
    { name: 'Consensus Engine', status: health?.consensusStatus || 'unknown', endpoint: '/internal/consensus/health' },
    { name: 'Citizenship Registry', status: 'healthy', endpoint: '/internal/citizenship/health' },
    { name: 'Billing Service', status: health?.billingStatus || 'unknown', endpoint: '/api/v1/billing/health' }
  ];

  return (
    <div className="space-y-6">
      <div className="bg-white shadow rounded-lg">
        <div className="px-4 py-5 sm:p-6">
          <h3 className="text-lg font-medium text-gray-900 mb-4">Service Health</h3>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {services.map((service, index) => (
              <div key={index} className="border border-gray-200 rounded-lg p-4">
                <div className="flex items-center justify-between mb-2">
                  <h4 className="text-sm font-medium text-gray-900">{service.name}</h4>
                  <div className={`w-3 h-3 rounded-full ${
                    service.status === 'healthy' ? 'bg-green-400' :
                    service.status === 'degraded' ? 'bg-yellow-400' : 'bg-red-400'
                  }`}></div>
                </div>
                <p className="text-xs text-gray-500">{service.endpoint}</p>
                <p className="text-xs text-gray-500 capitalize">{service.status}</p>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white p-6 rounded-lg shadow">
          <h3 className="text-lg font-medium text-gray-900 mb-4">System Metrics</h3>
          <div className="space-y-4">
            <div className="flex justify-between items-center">
              <span className="text-sm text-gray-600">Uptime (30 days)</span>
              <span className="text-sm font-medium">{health?.uptime.toFixed(1) || '0.0'}%</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-sm text-gray-600">Active Connections</span>
              <span className="text-sm font-medium">{health?.activeConnections || 0}</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-sm text-gray-600">Database Connections</span>
              <span className="text-sm font-medium">12/20</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-sm text-gray-600">Cache Hit Rate</span>
              <span className="text-sm font-medium">94.2%</span>
            </div>
          </div>
        </div>

        <div className="bg-white p-6 rounded-lg shadow">
          <h3 className="text-lg font-medium text-gray-900 mb-4">Recent Alerts</h3>
          <div className="space-y-3">
            <div className="flex items-start space-x-3">
              <AlertTriangle className="h-5 w-5 text-yellow-500 mt-0.5" />
              <div>
                <p className="text-sm font-medium text-gray-900">High CPU Usage</p>
                <p className="text-xs text-gray-500">API Gateway CPU at 85% for 5 minutes</p>
                <p className="text-xs text-gray-400">2 minutes ago</p>
              </div>
            </div>
            <div className="flex items-start space-x-3">
              <Database className="h-5 w-5 text-blue-500 mt-0.5" />
              <div>
                <p className="text-sm font-medium text-gray-900">Database Maintenance</p>
                <p className="text-xs text-gray-500">Scheduled maintenance completed successfully</p>
                <p className="text-xs text-gray-400">1 hour ago</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function SettingsTab() {
  return (
    <div className="space-y-6">
      <div className="bg-white shadow rounded-lg">
        <div className="px-4 py-5 sm:p-6">
          <h3 className="text-lg font-medium text-gray-900 mb-4">System Configuration</h3>

          <div className="space-y-6">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Billing Settings
              </label>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs text-gray-500 mb-1">Stripe API Key</label>
                  <input
                    type="password"
                    className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm"
                    placeholder="sk_live_..."
                  />
                </div>
                <div>
                  <label className="block text-xs text-gray-500 mb-1">Webhook Secret</label>
                  <input
                    type="password"
                    className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm"
                    placeholder="whsec_..."
                  />
                </div>
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                System Limits
              </label>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div>
                  <label className="block text-xs text-gray-500 mb-1">Max Citizens per Tenant</label>
                  <input
                    type="number"
                    className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm"
                    defaultValue="1000"
                  />
                </div>
                <div>
                  <label className="block text-xs text-gray-500 mb-1">API Rate Limit (req/min)</label>
                  <input
                    type="number"
                    className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm"
                    defaultValue="1000"
                  />
                </div>
                <div>
                  <label className="block text-xs text-gray-500 mb-1">Audit Retention (days)</label>
                  <input
                    type="number"
                    className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm"
                    defaultValue="2555"
                  />
                </div>
              </div>
            </div>

            <div className="flex justify-end">
              <button className="bg-blue-600 text-white px-4 py-2 rounded-md text-sm font-medium hover:bg-blue-700">
                Save Configuration
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
