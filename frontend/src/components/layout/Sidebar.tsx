import { NavLink } from 'react-router-dom';
import { LayoutDashboard, ArrowRightLeft, Briefcase, TrendingUp } from 'lucide-react';


export default function Sidebar() {
  const links = [
    { to: '/', label: 'Dashboard', icon: LayoutDashboard },
    { to: '/holdings', label: 'Holdings', icon: Briefcase },
    { to: '/transactions', label: 'Transactions', icon: ArrowRightLeft },
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
      <div className="p-4 border-t border-slate-900 text-xs text-slate-500 text-center">
        v0.4.0
      </div>
    </aside>
  );
}
