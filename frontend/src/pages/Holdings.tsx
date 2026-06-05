import { Info } from 'lucide-react';


export default function Holdings() {
  const mockHoldings = [
    {
      ticker: 'AAPL',
      name: 'Apple Inc.',
      shares: 6.0,
      avgCost: 150.0,
      currentPrice: 310.25,
      marketValue: 1861.50,
      unrealizedPnl: 961.50,
      unrealizedPnlPct: 106.83,
      realizedPnl: 80.00,
    },
    {
      ticker: 'MSFT',
      name: 'Microsoft Corporation',
      shares: 5.0,
      avgCost: 400.0,
      currentPrice: 429.73,
      marketValue: 2148.65,
      unrealizedPnl: 148.65,
      unrealizedPnlPct: 7.43,
      realizedPnl: 0.00,
    },
  ];

  const totalMarketValue = mockHoldings.reduce((sum, h) => sum + h.marketValue, 0);

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl font-bold tracking-tight text-white">Holdings</h1>
        <p className="text-sm text-slate-400">View and analyze your current active positions and P&L status.</p>
      </div>

      {/* Info banner */}
      <div className="flex gap-3 bg-blue-500/5 border border-blue-500/10 p-4 rounded-2xl text-sm text-blue-300 backdrop-blur-md">
        <Info className="h-5 w-5 shrink-0 text-blue-400" />
        <div>
          <span className="font-semibold">Note:</span> Weighted average cost basis is calculated dynamically based on FIFO accounting rules for remaining lot shares.
        </div>
      </div>

      {/* Holdings Table */}
      <div className="overflow-hidden rounded-2xl border border-slate-800 bg-slate-900/40 backdrop-blur-md shadow-sm">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="border-b border-slate-800 bg-slate-900/20 text-xs font-semibold uppercase tracking-wider text-slate-400">
                <th className="py-4.5 px-6">Asset</th>
                <th className="py-4.5 px-6 text-right">Shares Held</th>
                <th className="py-4.5 px-6 text-right">Avg. Cost Basis</th>
                <th className="py-4.5 px-6 text-right">Current Price</th>
                <th className="py-4.5 px-6 text-right">Market Value</th>
                <th className="py-4.5 px-6 text-right">Unrealized P&L</th>
                <th className="py-4.5 px-6 text-right">Realized P&L</th>
                <th className="py-4.5 px-6 text-right">Allocation</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 text-sm text-slate-300">
              {mockHoldings.map((h) => {
                const allocation = (h.marketValue / totalMarketValue) * 100;
                const isPnlPositive = h.unrealizedPnl >= 0;
                return (
                  <tr key={h.ticker} className="hover:bg-slate-900/20 transition-colors duration-150">
                    <td className="py-4.5 px-6 whitespace-nowrap">
                      <div className="flex items-center gap-3">
                        <div className="h-8 w-8 rounded-lg bg-slate-950 flex items-center justify-center font-bold text-xs text-emerald-400 border border-slate-800">
                          {h.ticker}
                        </div>
                        <div>
                          <div className="font-bold text-white leading-tight">{h.ticker}</div>
                          <div className="text-xs text-slate-500">{h.name}</div>
                        </div>
                      </div>
                    </td>
                    <td className="py-4.5 px-6 text-right font-mono whitespace-nowrap">{h.shares.toFixed(4)}</td>
                    <td className="py-4.5 px-6 text-right font-mono whitespace-nowrap">${h.avgCost.toFixed(2)}</td>
                    <td className="py-4.5 px-6 text-right font-mono whitespace-nowrap">${h.currentPrice.toFixed(2)}</td>
                    <td className="py-4.5 px-6 text-right font-mono font-semibold text-white whitespace-nowrap">
                      ${h.marketValue.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                    </td>
                    <td className="py-4.5 px-6 text-right font-mono whitespace-nowrap">
                      <div className={`flex items-center justify-end font-semibold ${isPnlPositive ? 'text-emerald-400' : 'text-red-400'}`}>
                        {isPnlPositive ? '+' : ''}${h.unrealizedPnl.toFixed(2)}
                        <span className="text-xs ml-1 font-normal">
                          ({isPnlPositive ? '+' : ''}{h.unrealizedPnlPct.toFixed(2)}%)
                        </span>
                      </div>
                    </td>
                    <td className="py-4.5 px-6 text-right font-mono whitespace-nowrap text-teal-400 font-medium">
                      +${h.realizedPnl.toFixed(2)}
                    </td>
                    <td className="py-4.5 px-6 text-right whitespace-nowrap">
                      <div className="flex items-center justify-end gap-2.5">
                        <span className="font-mono text-xs text-slate-400">{allocation.toFixed(1)}%</span>
                        <div className="w-16 bg-slate-950 rounded-full h-1.5 overflow-hidden border border-slate-800">
                          <div
                            className="bg-gradient-to-r from-emerald-500 to-teal-500 h-full rounded-full"
                            style={{ width: `${allocation}%` }}
                          ></div>
                        </div>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
