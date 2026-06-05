import { TrendingUp, Wallet, DollarSign, ArrowUpRight, Briefcase } from 'lucide-react';


export default function Dashboard() {
  const stats = [
    {
      label: 'Net Portfolio Value',
      value: '$11,190.15',
      change: '+10.2%',
      isPositive: true,
      icon: Wallet,
      colorClass: 'text-emerald-400 bg-emerald-500/10',
    },
    {
      label: 'Invested Capital',
      value: '$2,900.00',
      change: null,
      icon: DollarSign,
      colorClass: 'text-blue-400 bg-blue-500/10',
    },
    {
      label: 'Unrealized P&L',
      value: '+$1,110.15',
      change: '+38.28%',
      isPositive: true,
      icon: ArrowUpRight,
      colorClass: 'text-emerald-400 bg-emerald-500/10',
    },
    {
      label: 'Realized P&L',
      value: '+$80.00',
      change: null,
      icon: TrendingUp,
      colorClass: 'text-teal-400 bg-teal-500/10',
    },
    {
      label: 'Cash Balance',
      value: '$7,180.00',
      change: null,
      icon: Briefcase,
      colorClass: 'text-purple-400 bg-purple-500/10',
    },
  ];

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl font-bold tracking-tight text-white">Dashboard</h1>
        <p className="text-sm text-slate-400">Real-time overview of your net worth and holdings performance.</p>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-5">
        {stats.map((stat) => {
          const Icon = stat.icon;
          return (
            <div
              key={stat.label}
              className="relative overflow-hidden rounded-2xl border border-slate-800 bg-slate-900/40 p-5 shadow-sm backdrop-blur-md transition-all duration-200 hover:border-slate-700"
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

      {/* Chart Placeholders */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        {/* Performance Chart Placeholder */}
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
                  className={`px-3 py-1 text-xs font-medium rounded-md transition-all duration-150 ${
                    p === '1M' ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' : 'text-slate-400 hover:text-slate-200'
                  }`}
                >
                  {p}
                </button>
              ))}
            </div>
          </div>
          
          {/* Mock Chart Area */}
          <div className="flex-1 flex items-center justify-center border-2 border-dashed border-slate-800/80 rounded-xl my-6 bg-slate-950/40 relative overflow-hidden group">
            <div className="absolute inset-0 bg-gradient-to-t from-emerald-500/5 to-transparent"></div>
            <div className="text-center z-10">
              <TrendingUp className="h-10 w-10 text-emerald-500/40 mx-auto mb-2 group-hover:scale-110 transition-transform duration-200" />
              <p className="text-sm font-semibold text-slate-300">Historical performance chart will render here</p>
              <p className="text-xs text-slate-500 mt-1">TanStack Query + Recharts integration in next milestone</p>
            </div>
          </div>
        </div>

        {/* Asset Allocation Placeholder */}
        <div className="rounded-2xl border border-slate-800 bg-slate-900/40 p-6 backdrop-blur-md min-h-[400px] flex flex-col justify-between">
          <div>
            <h2 className="text-lg font-bold text-white">Asset Allocation</h2>
            <p className="text-xs text-slate-400">Distribution across tickers</p>
          </div>

          {/* Mock Pie Chart Area */}
          <div className="flex-1 flex items-center justify-center border-2 border-dashed border-slate-800/80 rounded-xl my-6 bg-slate-950/40 relative overflow-hidden group">
            <div className="absolute inset-0 bg-gradient-to-tr from-teal-500/5 to-transparent"></div>
            <div className="text-center z-10">
              <div className="relative h-24 w-24 mx-auto mb-4 flex items-center justify-center">
                <div className="absolute inset-0 rounded-full border-[10px] border-emerald-500/10 border-t-emerald-400 border-r-teal-400 group-hover:rotate-12 transition-transform duration-300"></div>
                <span className="text-xs font-bold text-emerald-400">AAPL/MSFT</span>
              </div>
              <p className="text-sm font-semibold text-slate-300">Allocation breakdown</p>
              <p className="text-xs text-slate-500 mt-1">Summary pie-chart integration pending</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
