import { NavLink } from 'react-router-dom';
import { LayoutDashboard, ArrowRightLeft, Briefcase, TrendingUp, BarChart3 } from 'lucide-react';
import { useCurrency } from '../../context/CurrencyContext';


export default function Sidebar() {
  const { currency, setCurrency } = useCurrency();
  
  const links = [
    { to: '/', label: 'Dashboard', icon: LayoutDashboard },
    { to: '/holdings', label: 'Holdings', icon: Briefcase },
    { to: '/transactions', label: 'Transactions', icon: ArrowRightLeft },
    { to: '/insights', label: 'Insights', icon: BarChart3 },
  ];

  return (
    <aside className="w-64 border-r border-slate-800 bg-slate-950/80 backdrop-blur-md flex flex-col h-screen sticky top-0">
      <div className="p-6 flex items-center gap-3 border-b border-slate-900">
        <TrendingUp className="h-6 w-6 text-emerald-400" />
        <span className="text-xl font-bold tracking-tight bg-gradient-to-r from-emerald-400 to-teal-400 bg-clip-text text-transparent">
          Folio
        </span>
      </div>
      <nav className="flex-1 p-4 space-y-1">
        {links.map(({ to, label, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) =>
              `flex items-center gap-3 px-4 py-3 rounded-lg text-sm font-medium transition-all duration-200 ${
                isActive
                  ? 'bg-emerald-500/10 text-emerald-400 border-l-2 border-emerald-500 pl-3.5'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900/50'
              }`
            }
          >
            <Icon className="h-5 w-5" />
            {label}
          </NavLink>
        ))}
      </nav>
      <div className="p-4 border-t border-slate-900 space-y-3">
        <div className="flex items-center justify-between text-xs text-slate-400 px-1 font-medium">
          <span>Display Currency</span>
        </div>
        <div className="grid grid-cols-2 gap-1 p-1 bg-slate-900 rounded-lg">
          <button
            onClick={() => setCurrency('USD')}
            className={`py-1.5 text-xs font-semibold rounded-md transition-all duration-200 cursor-pointer ${
              currency === 'USD'
                ? 'bg-slate-800 text-emerald-400 shadow-sm'
                : 'text-slate-500 hover:text-slate-300'
            }`}
          >
            USD ($)
          </button>
          <button
            onClick={() => setCurrency('INR')}
            className={`py-1.5 text-xs font-semibold rounded-md transition-all duration-200 cursor-pointer ${
              currency === 'INR'
                ? 'bg-slate-800 text-emerald-400 shadow-sm'
                : 'text-slate-500 hover:text-slate-300'
            }`}
          >
            INR (₹)
          </button>
        </div>
        <div className="text-center text-[10px] text-slate-600">
          v0.4.0
        </div>
      </div>
    </aside>
  );
}

