import { Plus, Search, Filter, Trash2, Calendar } from 'lucide-react';


export default function Transactions() {
  const mockTransactions = [
    {
      id: 3,
      date: '2026-06-03 11:00 AM',
      type: 'SELL',
      ticker: 'AAPL',
      quantity: 4.0,
      price: 170.0,
      total: 680.0,
      notes: 'Take partial profit',
      typeClass: 'bg-red-500/10 text-red-400 border border-red-500/20',
    },
    {
      id: 2,
      date: '2026-06-02 10:00 AM',
      type: 'BUY',
      ticker: 'AAPL',
      quantity: 10.0,
      price: 150.0,
      total: 1500.0,
      notes: 'Long term invest',
      typeClass: 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20',
    },
    {
      id: 1,
      date: '2026-06-01 00:00 AM',
      type: 'DEPOSIT',
      ticker: '—',
      quantity: '—',
      price: '—',
      total: 10000.0,
      notes: 'Initial funding',
      typeClass: 'bg-purple-500/10 text-purple-400 border border-purple-500/20',
    },
  ];

  return (
    <div className="space-y-8">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-white">Transactions</h1>
          <p className="text-sm text-slate-400">Add, track, and manage your account transactions.</p>
        </div>
        <button
          className="inline-flex items-center justify-center gap-2 px-4 py-2.5 bg-gradient-to-r from-emerald-500 to-teal-500 text-slate-950 font-semibold text-sm rounded-xl hover:opacity-90 shadow-lg hover:shadow-emerald-500/10 transition-all duration-200 cursor-pointer"
        >
          <Plus className="h-5 w-5 stroke-[2.5]" />
          Add Trade
        </button>
      </div>

      {/* Filters and Search Bar */}
      <div className="flex flex-col sm:flex-row gap-3 bg-slate-900/40 p-4 rounded-2xl border border-slate-800 backdrop-blur-md">
        <div className="relative flex-1">
          <Search className="absolute left-3.5 top-3 h-5 w-5 text-slate-500" />
          <input
            type="text"
            placeholder="Search by ticker or notes..."
            className="w-full bg-slate-950 border border-slate-800 rounded-xl pl-11 pr-4 py-2 text-sm text-slate-300 placeholder-slate-500 focus:outline-none focus:border-slate-700 transition-colors"
          />
        </div>
        <div className="flex gap-2">
          <button className="flex items-center gap-2 px-4 py-2 bg-slate-950 border border-slate-800 rounded-xl text-sm text-slate-400 hover:text-slate-200 hover:border-slate-700 transition-all duration-150">
            <Filter className="h-4 w-4" />
            Filter
          </button>
          <button className="flex items-center gap-2 px-4 py-2 bg-slate-950 border border-slate-800 rounded-xl text-sm text-slate-400 hover:text-slate-200 hover:border-slate-700 transition-all duration-150">
            <Calendar className="h-4 w-4" />
            Date
          </button>
        </div>
      </div>

      {/* Transactions Table */}
      <div className="overflow-hidden rounded-2xl border border-slate-800 bg-slate-900/40 backdrop-blur-md shadow-sm">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="border-b border-slate-800 bg-slate-900/20 text-xs font-semibold uppercase tracking-wider text-slate-400">
                <th className="py-4.5 px-6">Date</th>
                <th className="py-4.5 px-6">Type</th>
                <th className="py-4.5 px-6">Ticker</th>
                <th className="py-4.5 px-6 text-right">Quantity</th>
                <th className="py-4.5 px-6 text-right">Price</th>
                <th className="py-4.5 px-6 text-right">Total Amount</th>
                <th className="py-4.5 px-6">Notes</th>
                <th className="py-4.5 px-6 text-center">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 text-sm text-slate-300">
              {mockTransactions.map((tx) => (
                <tr key={tx.id} className="hover:bg-slate-900/20 transition-colors duration-150">
                  <td className="py-4 px-6 text-xs text-slate-400 whitespace-nowrap">{tx.date}</td>
                  <td className="py-4 px-6 whitespace-nowrap">
                    <span className={`inline-flex px-2 py-0.5 rounded-full text-xs font-semibold ${tx.typeClass}`}>
                      {tx.type}
                    </span>
                  </td>
                  <td className="py-4 px-6 font-bold text-white whitespace-nowrap">{tx.ticker}</td>
                  <td className="py-4 px-6 text-right font-mono whitespace-nowrap">{tx.quantity}</td>
                  <td className="py-4 px-6 text-right font-mono whitespace-nowrap">
                    {typeof tx.price === 'number' ? `$${tx.price.toFixed(2)}` : tx.price}
                  </td>
                  <td className="py-4 px-6 text-right font-mono font-semibold text-white whitespace-nowrap">
                    ${tx.total.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                  </td>
                  <td className="py-4 px-6 max-w-xs truncate text-slate-400" title={tx.notes}>
                    {tx.notes}
                  </td>
                  <td className="py-4 px-6 text-center whitespace-nowrap">
                    <button className="text-slate-500 hover:text-red-400 p-1.5 rounded-lg hover:bg-slate-950 transition-all duration-150 cursor-pointer">
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
