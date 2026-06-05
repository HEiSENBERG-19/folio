import { useState } from 'react';
import Sidebar from './Sidebar';
import { Menu, X } from 'lucide-react';


interface AppShellProps {
  children: React.ReactNode;
}

export default function AppShell({ children }: AppShellProps) {
  const [isMobileOpen, setIsMobileOpen] = useState(false);

  return (
    <div className="flex min-h-screen bg-slate-950 text-slate-100">
      {/* Desktop Sidebar */}
      <div className="hidden md:flex">
        <Sidebar />
      </div>

      {/* Mobile Drawer Sidebar */}
      {isMobileOpen && (
        <div className="fixed inset-0 z-50 flex md:hidden bg-slate-950/80 backdrop-blur-sm">
          <div className="relative w-64">
            <Sidebar />
            <button
              onClick={() => setIsMobileOpen(false)}
              className="absolute top-4 right-[-48px] p-2 bg-slate-900 border border-slate-800 text-slate-400 rounded-lg focus:outline-none"
            >
              <X className="h-6 w-6" />
            </button>
          </div>
          <div className="flex-1" onClick={() => setIsMobileOpen(false)} />
        </div>
      )}

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Mobile Header */}
        <header className="flex md:hidden items-center justify-between px-6 py-4 border-b border-slate-900 bg-slate-950/90 backdrop-blur-md sticky top-0 z-40">
          <span className="text-xl font-bold bg-gradient-to-r from-emerald-400 to-teal-400 bg-clip-text text-transparent">
            Folio
          </span>
          <button
            onClick={() => setIsMobileOpen(true)}
            className="p-2 text-slate-400 hover:text-slate-200 focus:outline-none"
          >
            <Menu className="h-6 w-6" />
          </button>
        </header>

        {/* Dynamic page content */}
        <main className="flex-1 p-6 md:p-10 max-w-7xl w-full mx-auto animate-fade-in">
          {children}
        </main>
      </div>
    </div>
  );
}
