import { useState } from 'react';
import { TrendingUp, Wallet, IndianRupee, ArrowUpRight, Briefcase } from 'lucide-react';
import { usePortfolioSummary, usePortfolioHistory, usePortfolioAllocation } from '../hooks/usePortfolio';
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  Legend,
} from 'recharts';
import { useCurrency } from '../context/CurrencyContext';

const COLORS = ['#10b981', '#06b6d4', '#3b82f6', '#8b5cf6', '#ec4899', '#f59e0b'];

const formatPercent = (val: number) => {
  const sign = val >= 0 ? '+' : '';
  return `${sign}${val.toFixed(2)}%`;
};

interface CustomHistoryTooltipProps {
  active?: boolean;
  payload?: Array<{ payload: { total_value: number; portfolio_value: number; cash_balance: number } }>;
  label?: string;
  formatCurrency: (value: number | null | undefined) => string;
}

const CustomHistoryTooltip = ({ active, payload, label, formatCurrency }: CustomHistoryTooltipProps) => {
  if (active && payload && payload.length) {
    const data = payload[0].payload;
    return (
      <div className="bg-slate-900 border border-slate-800 p-4 rounded-xl shadow-lg backdrop-blur-md">
        <p className="text-xs font-semibold text-slate-400">{label}</p>
        <p className="text-sm font-bold text-emerald-400 mt-1">
          Total: {formatCurrency(data.total_value)}
        </p>
        <p className="text-xs text-slate-300 mt-0.5">
          Stock: {formatCurrency(data.portfolio_value)}
        </p>
        <p className="text-xs text-slate-300">
          Cash: {formatCurrency(data.cash_balance)}
        </p>
      </div>
    );
  }
  return null;
};

interface CustomAllocationTooltipProps {
  active?: boolean;
  payload?: Array<{ payload: { ticker: string; market_value: number; percentage: number } }>;
  formatCurrency: (value: number | null | undefined) => string;
}

const CustomAllocationTooltip = ({ active, payload, formatCurrency }: CustomAllocationTooltipProps) => {
  if (active && payload && payload.length) {
    const data = payload[0].payload;
    return (
      <div className="bg-slate-900 border border-slate-800 p-3 rounded-xl shadow-lg backdrop-blur-md">
        <p className="text-sm font-bold text-white">{data.ticker}</p>
        <p className="text-xs text-slate-300 mt-1">
          Market Value: {formatCurrency(data.market_value)}
        </p>
        <p className="text-xs font-semibold text-emerald-400">
          Percentage: {data.percentage.toFixed(2)}%
        </p>
      </div>
    );
  }
  return null;
};

export default function Dashboard() {
  const [period, setPeriod] = useState<string>('1Y');
  const { formatCurrency, currencySymbol } = useCurrency();

  const { data: summary, isLoading: summaryLoading } = usePortfolioSummary();
  const { data: history, isLoading: historyLoading } = usePortfolioHistory(period);
  const { data: allocation, isLoading: allocationLoading } = usePortfolioAllocation();

  const unrealizedPnlPct = summary?.total_invested
    ? (summary.total_unrealized_pnl / summary.total_invested) * 100
    : 0;

  const stats = [
    {
      label: 'Net Portfolio Value',
      value: summary ? formatCurrency(summary.net_portfolio_value) : formatCurrency(0),
      change: null,
      icon: Wallet,
      colorClass: 'text-emerald-400 bg-emerald-500/10',
    },
    {
      label: 'Invested Capital',
      value: summary ? formatCurrency(summary.total_invested) : formatCurrency(0),
      change: null,
      icon: IndianRupee,
      colorClass: 'text-blue-400 bg-blue-500/10',
    },
    {
      label: 'Unrealized P&L',
      value: summary ? `${summary.total_unrealized_pnl >= 0 ? '+' : ''}${formatCurrency(summary.total_unrealized_pnl)}` : formatCurrency(0),
      change: summary ? formatPercent(unrealizedPnlPct) : null,
      isPositive: summary ? summary.total_unrealized_pnl >= 0 : true,
      icon: ArrowUpRight,
      colorClass: summary && summary.total_unrealized_pnl >= 0 ? 'text-emerald-400 bg-emerald-500/10' : 'text-red-400 bg-red-500/10',
    },
    {
      label: 'Realized P&L',
      value: summary ? `${summary.total_realized_pnl >= 0 ? '+' : ''}${formatCurrency(summary.total_realized_pnl)}` : formatCurrency(0),
      change: null,
      icon: TrendingUp,
      colorClass: summary && summary.total_realized_pnl >= 0 ? 'text-teal-400 bg-teal-500/10' : 'text-red-400 bg-red-500/10',
    },
    {
      label: 'Cash Balance',
      value: summary ? formatCurrency(summary.total_cash) : formatCurrency(0),
      change: null,
      icon: Briefcase,
      colorClass: 'text-purple-400 bg-purple-500/10',
    },
  ];

  // Custom tooltips are defined outside of the component to prevent recreation during render.

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl font-bold tracking-tight text-white">Dashboard</h1>
        <p className="text-sm text-slate-400">Real-time overview of your net worth and holdings performance.</p>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-5">
        {summaryLoading
          ? Array.from({ length: 5 }).map((_, i) => (
              <div
                key={i}
                data-testid="stat-card"
                className="relative overflow-hidden rounded-2xl border border-slate-800 bg-slate-900/40 p-5 shadow-sm backdrop-blur-md stat-card"
              >
                <div className="flex items-center justify-between">
                  <div className="h-4 w-24 bg-slate-800 rounded animate-pulse" />
                  <div className="h-9 w-9 bg-slate-800 rounded-xl animate-pulse" />
                </div>
                <div className="mt-4 flex items-baseline gap-2">
                  <div className="h-8 w-28 bg-slate-800 rounded animate-pulse" />
                </div>
              </div>
            ))
          : stats.map((stat) => {
              const Icon = stat.icon;
              return (
                <div
                  key={stat.label}
                  data-testid="stat-card"
                  className="relative overflow-hidden rounded-2xl border border-slate-800 bg-slate-900/40 p-5 shadow-sm backdrop-blur-md transition-all duration-200 hover:border-slate-700 stat-card"
                >
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">{stat.label}</span>
                    <div className={`p-2 rounded-xl ${stat.colorClass}`}>
                      <Icon className="h-5 w-5" />
                    </div>
                  </div>
                  <div className="mt-4 flex items-baseline gap-2">
                    <span className="text-2xl font-bold text-white tracking-tight">{stat.value}</span>
                    {stat.change && (
                      <span
                        className={`inline-flex items-center text-xs font-semibold ${
                          stat.isPositive ? 'text-emerald-400' : 'text-red-400'
                        }`}
                      >
                        {stat.change}
                      </span>
                    )}
                  </div>
                </div>
              );
            })}
      </div>

      {/* Charts Section */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        {/* Performance Chart */}
        <div className="lg:col-span-2 rounded-2xl border border-slate-800 bg-slate-900/40 p-6 backdrop-blur-md min-h-[400px] flex flex-col justify-between">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-lg font-bold text-white">Portfolio Performance</h2>
              <p className="text-xs text-slate-400">Net portfolio value history</p>
            </div>
            <div className="flex gap-2 bg-slate-900 p-1 rounded-lg border border-slate-800">
              {['1M', '3M', '6M', '1Y', 'ALL'].map((p) => (
                <button
                  key={p}
                  onClick={() => setPeriod(p)}
                  className={`px-3 py-1 text-xs font-medium rounded-md transition-all duration-150 cursor-pointer ${
                    p === period
                      ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                      : 'text-slate-400 hover:text-slate-200'
                  }`}
                >
                  {p}
                </button>
              ))}
            </div>
          </div>

          {historyLoading ? (
            <div className="flex-1 flex items-center justify-center border border-dashed border-slate-800/80 rounded-xl my-6 bg-slate-950/40 relative overflow-hidden group">
              <div className="text-center z-10 animate-pulse">
                <TrendingUp className="h-10 w-10 text-slate-600 mx-auto mb-2" />
                <p className="text-sm font-semibold text-slate-500">Loading performance data...</p>
              </div>
            </div>
          ) : !history || !history.data_points || history.data_points.length === 0 ? (
            <div className="flex-1 flex items-center justify-center border border-dashed border-slate-800/80 rounded-xl my-6 bg-slate-950/40 relative overflow-hidden group">
              <div className="absolute inset-0 bg-gradient-to-t from-emerald-500/5 to-transparent"></div>
              <div className="text-center z-10 p-6">
                <TrendingUp className="h-10 w-10 text-emerald-500/40 mx-auto mb-2" />
                <p className="text-sm font-semibold text-slate-300">No historical performance data</p>
                <p className="text-xs text-slate-500 mt-1">Add transactions to start tracking performance over time.</p>
              </div>
            </div>
          ) : (
            <div className="flex-1 h-64 my-6">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={history.data_points}>
                  <defs>
                    <linearGradient id="colorTotal" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#10b981" stopOpacity={0.3}/>
                      <stop offset="95%" stopColor="#10b981" stopOpacity={0}/>
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" opacity={0.4} />
                  <XAxis
                    dataKey="date"
                    stroke="#64748b"
                    fontSize={11}
                    tickLine={false}
                    axisLine={false}
                  />
                  <YAxis
                    stroke="#64748b"
                    fontSize={11}
                    tickLine={false}
                    axisLine={false}
                    tickFormatter={(val) => `${currencySymbol}${val}`}
                  />
                  <Tooltip content={<CustomHistoryTooltip formatCurrency={formatCurrency} />} />
                  <Area
                    type="monotone"
                    dataKey="total_value"
                    stroke="#10b981"
                    strokeWidth={2}
                    fillOpacity={1}
                    fill="url(#colorTotal)"
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          )}
        </div>

        {/* Asset Allocation */}
        <div className="rounded-2xl border border-slate-800 bg-slate-900/40 p-6 backdrop-blur-md min-h-[400px] flex flex-col justify-between">
          <div>
            <h2 className="text-lg font-bold text-white">Asset Allocation</h2>
            <p className="text-xs text-slate-400">Distribution across tickers</p>
          </div>

          {allocationLoading ? (
            <div className="flex-1 flex items-center justify-center border border-dashed border-slate-800/80 rounded-xl my-6 bg-slate-950/40 relative overflow-hidden group">
              <div className="text-center z-10 animate-pulse">
                <div className="h-16 w-16 mx-auto mb-4 rounded-full border-[6px] border-slate-800 border-t-slate-600 animate-spin"></div>
                <p className="text-sm font-semibold text-slate-500">Loading allocation...</p>
              </div>
            </div>
          ) : !allocation || allocation.length === 0 ? (
            <div className="flex-1 flex items-center justify-center border border-dashed border-slate-800/80 rounded-xl my-6 bg-slate-950/40 relative overflow-hidden group">
              <div className="text-center z-10 p-6">
                <Briefcase className="h-10 w-10 text-teal-500/40 mx-auto mb-2" />
                <p className="text-sm font-semibold text-slate-300">No assets allocated</p>
                <p className="text-xs text-slate-500 mt-1">Add stock purchases to see asset allocation.</p>
              </div>
            </div>
          ) : (
            <div className="flex-1 h-64 my-6 flex flex-col justify-center">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={allocation}
                    dataKey="market_value"
                    nameKey="ticker"
                    cx="50%"
                    cy="50%"
                    innerRadius={60}
                    outerRadius={80}
                    paddingAngle={2}
                  >
                    {allocation.map((_entry, index) => (
                      <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip content={<CustomAllocationTooltip formatCurrency={formatCurrency} />} />
                  <Legend
                    verticalAlign="bottom"
                    height={36}
                    iconType="circle"
                    iconSize={8}
                    formatter={(value) => <span className="text-xs font-semibold text-slate-400">{value}</span>}
                  />
                </PieChart>
              </ResponsiveContainer>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
