import { Info } from 'lucide-react';
import { usePortfolioSummary } from '../hooks/usePortfolio';

const formatCurrency = (val: number) => {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
  }).format(val);
};

export default function Holdings() {
  const { data: summary, isLoading } = usePortfolioSummary();

  const holdings = summary?.holdings || [];
  const totalMarketValue = holdings.reduce((sum, h) => sum + h.market_value, 0);
  const totalUnrealizedPnl = holdings.reduce((sum, h) => sum + h.unrealized_pnl, 0);
  const totalRealizedPnl = holdings.reduce((sum, h) => sum + h.realized_pnl, 0);
  
  const totalCostBasis = holdings.reduce((sum, h) => sum + (h.total_shares * h.avg_cost_basis), 0);
  const totalUnrealizedPnlPct = totalCostBasis > 0 ? (totalUnrealizedPnl / totalCostBasis) * 100 : 0;

  const isTotalUnrealizedPositive = totalUnrealizedPnl >= 0;

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
              {isLoading ? (
                Array.from({ length: 3 }).map((_, i) => (
                  <tr key={i} className="animate-pulse">
                    <td className="py-4.5 px-6">
                      <div className="flex items-center gap-3">
                        <div className="h-8 w-8 rounded-lg bg-slate-800" />
                        <div className="space-y-1">
                          <div className="h-4 w-12 bg-slate-800 rounded" />
                          <div className="h-3 w-20 bg-slate-800 rounded" />
                        </div>
                      </div>
                    </td>
                    <td className="py-4.5 px-6"><div className="h-4 w-16 bg-slate-800 rounded ml-auto" /></td>
                    <td className="py-4.5 px-6"><div className="h-4 w-16 bg-slate-800 rounded ml-auto" /></td>
                    <td className="py-4.5 px-6"><div className="h-4 w-16 bg-slate-800 rounded ml-auto" /></td>
                    <td className="py-4.5 px-6"><div className="h-4 w-20 bg-slate-800 rounded ml-auto" /></td>
                    <td className="py-4.5 px-6"><div className="h-4 w-24 bg-slate-800 rounded ml-auto" /></td>
                    <td className="py-4.5 px-6"><div className="h-4 w-16 bg-slate-800 rounded ml-auto" /></td>
                    <td className="py-4.5 px-6"><div className="h-4 w-24 bg-slate-800 rounded ml-auto" /></td>
                  </tr>
                ))
              ) : holdings.length === 0 ? (
                <tr>
                  <td colSpan={8} className="py-12 text-center text-slate-500 font-medium">
                    No active positions. Add BUY transactions to see holdings.
                  </td>
                </tr>
              ) : (
                <>
                  {holdings.map((h) => {
                    const allocation = totalMarketValue > 0 ? (h.market_value / totalMarketValue) * 100 : 0;
                    const isPnlPositive = h.unrealized_pnl >= 0;
                    const isRealizedPositive = h.realized_pnl >= 0;
                    return (
                      <tr key={h.ticker} className="hover:bg-slate-900/20 transition-colors duration-150">
                        <td className="py-4.5 px-6 whitespace-nowrap">
                          <div className="flex items-center gap-3">
                            <div className="h-8 w-8 rounded-lg bg-slate-950 flex items-center justify-center font-bold text-xs text-emerald-400 border border-slate-800">
                              {h.ticker}
                            </div>
                            <div>
                              <div className="font-bold text-white leading-tight">{h.ticker}</div>
                              <div className="text-xs text-slate-500">{h.asset_name}</div>
                            </div>
                          </div>
                        </td>
                        <td className="py-4.5 px-6 text-right font-mono whitespace-nowrap">{h.total_shares.toFixed(4)}</td>
                        <td className="py-4.5 px-6 text-right font-mono whitespace-nowrap">{formatCurrency(h.avg_cost_basis)}</td>
                        <td className="py-4.5 px-6 text-right font-mono whitespace-nowrap">{formatCurrency(h.current_price)}</td>
                        <td className="py-4.5 px-6 text-right font-mono font-semibold text-white whitespace-nowrap">
                          {formatCurrency(h.market_value)}
                        </td>
                        <td className="py-4.5 px-6 text-right font-mono whitespace-nowrap">
                          <div className={`flex items-center justify-end font-semibold ${isPnlPositive ? 'text-emerald-400' : 'text-red-400'}`}>
                            {isPnlPositive ? '+' : ''}{formatCurrency(h.unrealized_pnl)}
                            <span className="text-xs ml-1 font-normal">
                              ({isPnlPositive ? '+' : ''}{h.unrealized_pnl_pct.toFixed(2)}%)
                            </span>
                          </div>
                        </td>
                        <td className={`py-4.5 px-6 text-right font-mono whitespace-nowrap font-medium ${isRealizedPositive ? 'text-teal-400' : 'text-red-400'}`}>
                          {isRealizedPositive ? '+' : ''}{formatCurrency(h.realized_pnl)}
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
                  {/* Totals Row */}
                  <tr className="border-t border-slate-800 bg-slate-900/10 font-semibold text-slate-200">
                    <td className="py-4.5 px-6 text-white font-bold">Totals</td>
                    <td className="py-4.5 px-6 text-right">—</td>
                    <td className="py-4.5 px-6 text-right">—</td>
                    <td className="py-4.5 px-6 text-right">—</td>
                    <td className="py-4.5 px-6 text-right font-mono text-white whitespace-nowrap">
                      {formatCurrency(totalMarketValue)}
                    </td>
                    <td className="py-4.5 px-6 text-right font-mono whitespace-nowrap">
                      <div className={`flex items-center justify-end font-bold ${isTotalUnrealizedPositive ? 'text-emerald-400' : 'text-red-400'}`}>
                        {isTotalUnrealizedPositive ? '+' : ''}{formatCurrency(totalUnrealizedPnl)}
                        <span className="text-xs ml-1 font-normal">
                          ({isTotalUnrealizedPositive ? '+' : ''}{totalUnrealizedPnlPct.toFixed(2)}%)
                        </span>
                      </div>
                    </td>
                    <td className={`py-4.5 px-6 text-right font-mono whitespace-nowrap font-bold ${totalRealizedPnl >= 0 ? 'text-teal-400' : 'text-red-400'}`}>
                      {totalRealizedPnl >= 0 ? '+' : ''}{formatCurrency(totalRealizedPnl)}
                    </td>
                    <td className="py-4.5 px-6 text-right whitespace-nowrap font-mono text-xs text-slate-400">
                      100.0%
                    </td>
                  </tr>
                </>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
