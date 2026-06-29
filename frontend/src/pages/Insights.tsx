import { usePortfolioInsights } from '../hooks/usePortfolio';
import { useCurrency } from '../context/CurrencyContext';
import { Treemap, ResponsiveContainer } from 'recharts';
import {
  TrendingUp,
  Percent,
  Activity,
  DollarSign,
  Compass,
  AlertCircle
} from 'lucide-react';
import AllocationDonutChart from '../components/charts/AllocationDonutChart';

const COLORS = ['#10b981', '#06b6d4', '#3b82f6', '#8b5cf6', '#ec4899', '#f59e0b', '#14b8a6', '#6366f1'];

interface CustomTreemapContentProps {
  x?: number;
  y?: number;
  width?: number;
  height?: number;
  name?: string;
  unrealized_pnl_pct?: number;
}

const CustomTreemapContent = (props: CustomTreemapContentProps) => {
  const { x = 0, y = 0, width = 0, height = 0, name = '', unrealized_pnl_pct } = props;
  if (width < 25 || height < 15) return null;

  let color = '#475569';
  if (unrealized_pnl_pct !== undefined && unrealized_pnl_pct !== null) {
    const p = unrealized_pnl_pct;
    if (p > 0) {
      const ratio = Math.min(p / 15, 1);
      const r = Math.round(71 + (16 - 71) * ratio);
      const g = Math.round(85 + (185 - 85) * ratio);
      const b = Math.round(105 + (129 - 105) * ratio);
      color = `rgb(${r}, ${g}, ${b})`;
    } else if (p < 0) {
      const ratio = Math.min(Math.abs(p) / 15, 1);
      const r = Math.round(71 + (244 - 71) * ratio);
      const g = Math.round(85 + (63 - 85) * ratio);
      const b = Math.round(105 + (94 - 105) * ratio);
      color = `rgb(${r}, ${g}, ${b})`;
    }
  }

  return (
    <g>
      <rect
        x={x}
        y={y}
        width={width}
        height={height}
        style={{
          fill: color,
          stroke: '#0f172a',
          strokeWidth: 2,
          strokeOpacity: 1,
        }}
      />
      {width > 45 && height > 30 && (
        <text
          x={x + width / 2}
          y={y + height / 2 - 3}
          textAnchor="middle"
          fill="#fff"
          fontSize={11}
          fontWeight="600"
        >
          {name}
        </text>
      )}
      {width > 60 && height > 45 && (
        <text
          x={x + width / 2}
          y={y + height / 2 + 11}
          textAnchor="middle"
          fill="#e2e8f0"
          fontSize={9.5}
          fontWeight="500"
        >
          {unrealized_pnl_pct !== undefined ? `${unrealized_pnl_pct >= 0 ? '+' : ''}${unrealized_pnl_pct.toFixed(1)}%` : ''}
        </text>
      )}
    </g>
  );
};

export default function Insights() {
  const { formatCurrency } = useCurrency();
  const { data, isLoading, isError } = usePortfolioInsights();

  if (isLoading) {
    return (
      <div className="space-y-8 animate-pulse">
        <div>
          <div className="h-8 w-48 bg-slate-800 rounded mb-2" />
          <div className="h-4 w-96 bg-slate-800 rounded" />
        </div>
        <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="h-28 bg-slate-800/40 rounded-2xl border border-slate-800" />
          ))}
        </div>
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
          <div className="h-80 bg-slate-800/40 rounded-2xl border border-slate-800" />
          <div className="h-80 bg-slate-800/40 rounded-2xl border border-slate-800" />
        </div>
      </div>
    );
  }

  if (isError || !data) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[400px] border border-slate-800 bg-slate-900/40 rounded-2xl p-8 backdrop-blur-md">
        <AlertCircle className="h-12 w-12 text-red-400 mb-4" />
        <h2 className="text-xl font-bold text-white mb-2">Error Loading Insights</h2>
        <p className="text-slate-400 text-sm text-center max-w-md">
          Could not fetch insights data from the server. Please check your connection and try again.
        </p>
      </div>
    );
  }

  const { holdings, cash_balances } = data;

  const normalizedHoldings = holdings.map(h => {
    const mv = h.market_value_native;
    const cost = h.market_value_native - h.unrealized_pnl_native;
    const pnl = mv - cost;
    const pnlPct = cost > 0 ? (pnl / cost) * 100 : 0;
    return {
      ...h,
      marketValue: mv,
      unrealizedPnl: pnl,
      unrealizedPnlPct: pnlPct
    };
  });

  const normalizedCash = cash_balances.map(c => ({
    ...c,
    cashBalance: c.cash_balance_native,
    stockValue: c.stock_value_native
  }));

  const holdingsVal = normalizedHoldings.reduce((sum, h) => sum + h.marketValue, 0);
  const cashVal = normalizedCash.reduce((sum, c) => sum + c.cashBalance, 0);
  const totalVal = holdingsVal + cashVal;

  if (totalVal === 0) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-white">Portfolio Insights</h1>
          <p className="text-sm text-slate-400">Deep financial analytics and asset allocation breakdown.</p>
        </div>
        <div className="flex flex-col items-center justify-center min-h-[400px] border border-slate-800 bg-slate-900/40 rounded-2xl p-8 backdrop-blur-md text-center">
          <div className="p-4 rounded-full bg-slate-800/60 mb-4">
            <Compass className="h-10 w-10 text-emerald-400" />
          </div>
          <h2 className="text-xl font-bold text-white mb-2">No Portfolio Data Available</h2>
          <p className="text-slate-400 text-sm max-w-sm">
            Add cash deposits or buy transactions to generate allocations, risk analysis, and valuation insights.
          </p>
        </div>
      </div>
    );
  }

  const holdingsWithBeta = normalizedHoldings.filter(h => h.beta !== null && h.beta !== undefined);
  const sumBetaMV = holdingsWithBeta.reduce((sum, h) => sum + (h.beta || 0) * h.marketValue, 0);
  const weightedBeta = totalVal > 0 ? sumBetaMV / totalVal : 0;

  const holdingsWithPE = normalizedHoldings.filter(h => h.trailing_pe && h.trailing_pe > 0);
  const peValSum = holdingsWithPE.reduce((sum, h) => sum + h.marketValue, 0);
  const sumPEMV = holdingsWithPE.reduce((sum, h) => sum + (h.trailing_pe || 0) * h.marketValue, 0);
  const weightedPE = peValSum > 0 ? sumPEMV / peValSum : null;

  const sumYieldMV = normalizedHoldings.reduce((sum, h) => sum + (h.dividend_yield || 0) * h.marketValue, 0);
  const weightedDivYield = holdingsVal > 0 ? (sumYieldMV / holdingsVal) * 100 : 0;

  const holdingsWithPB = normalizedHoldings.filter(h => h.price_to_book && h.price_to_book > 0);
  const pbValSum = holdingsWithPB.reduce((sum, h) => sum + h.marketValue, 0);
  const sumPBMV = holdingsWithPB.reduce((sum, h) => sum + (h.price_to_book || 0) * h.marketValue, 0);
  const weightedPB = pbValSum > 0 ? sumPBMV / pbValSum : null;

  const sectorMap: { [key: string]: number } = {};
  normalizedHoldings.forEach(h => {
    const sec = h.sector || 'Other';
    sectorMap[sec] = (sectorMap[sec] || 0) + h.marketValue;
  });
  const sectorDataRaw = Object.entries(sectorMap)
    .map(([name, value]) => ({ name, value }))
    .filter(item => item.value > 0);
  const sectorTotal = sectorDataRaw.reduce((sum, item) => sum + item.value, 0);
  const sectorData = sectorDataRaw.map(item => ({
    ...item,
    percentage: sectorTotal > 0 ? (item.value / sectorTotal) * 100 : 0
  })).sort((a, b) => b.value - a.value);

  const typeMap: { [key: string]: number } = {};
  normalizedHoldings.forEach(h => {
    typeMap[h.asset_class] = (typeMap[h.asset_class] || 0) + h.marketValue;
  });
  if (cashVal > 0) {
    typeMap['Cash'] = cashVal;
  }
  const typeDataRaw = Object.entries(typeMap)
    .map(([name, value]) => ({ name, value }))
    .filter(item => item.value > 0);
  const typeTotal = typeDataRaw.reduce((sum, item) => sum + item.value, 0);
  const typeData = typeDataRaw.map(item => ({
    ...item,
    percentage: typeTotal > 0 ? (item.value / typeTotal) * 100 : 0
  })).sort((a, b) => b.value - a.value);

  const countryMap: { [key: string]: number } = {};
  normalizedHoldings.forEach(h => {
    const c = h.country || 'Other';
    countryMap[c] = (countryMap[c] || 0) + h.marketValue;
  });
  normalizedCash.forEach(c => {
    const country = c.currency === 'INR' ? 'India' : 'United States';
    countryMap[country] = (countryMap[country] || 0) + c.cashBalance;
  });
  const countryDataRaw = Object.entries(countryMap)
    .map(([name, value]) => ({ name, value }))
    .filter(item => item.value > 0);
  const countryTotal = countryDataRaw.reduce((sum, item) => sum + item.value, 0);
  const countryData = countryDataRaw.map(item => ({
    ...item,
    percentage: countryTotal > 0 ? (item.value / countryTotal) * 100 : 0
  })).sort((a, b) => b.value - a.value);

  const currMap: { [key: string]: number } = {};
  normalizedHoldings.forEach(h => {
    currMap[h.currency] = (currMap[h.currency] || 0) + h.marketValue;
  });
  normalizedCash.forEach(c => {
    currMap[c.currency] = (currMap[c.currency] || 0) + c.cashBalance;
  });
  const currencyDataRaw = Object.entries(currMap)
    .map(([name, value]) => ({ name, value }))
    .filter(item => item.value > 0);
  const currencyTotal = currencyDataRaw.reduce((sum, item) => sum + item.value, 0);
  const currencyData = currencyDataRaw.map(item => ({
    ...item,
    percentage: currencyTotal > 0 ? (item.value / currencyTotal) * 100 : 0
  })).sort((a, b) => b.value - a.value);

  const accountMap: { [key: string]: number } = {};
  normalizedCash.forEach(c => {
    accountMap[c.account_name] = c.cashBalance + c.stockValue;
  });
  const accountDataRaw = Object.entries(accountMap)
    .map(([name, value]) => ({ name, value }))
    .filter(item => item.value > 0);
  const accountTotal = accountDataRaw.reduce((sum, item) => sum + item.value, 0);
  const accountData = accountDataRaw.map(item => ({
    ...item,
    percentage: accountTotal > 0 ? (item.value / accountTotal) * 100 : 0
  })).sort((a, b) => b.value - a.value);

  let lowRiskVal = 0;
  let medRiskVal = 0;
  let highRiskVal = 0;
  normalizedHoldings.forEach(h => {
    const b = h.beta ?? 1.0;
    if (b <= 0.8) lowRiskVal += h.marketValue;
    else if (b > 1.2) highRiskVal += h.marketValue;
    else medRiskVal += h.marketValue;
  });
  const riskItems = [
    { name: 'Cash', value: cashVal, color: '#64748b' },
    { name: 'Low Risk (Beta ≤ 0.8)', value: lowRiskVal, color: '#10b981' },
    { name: 'Medium Risk (0.8 < Beta ≤ 1.2)', value: medRiskVal, color: '#3b82f6' },
    { name: 'High Risk (Beta > 1.2)', value: highRiskVal, color: '#ef4444' }
  ].filter(r => r.value > 0);
  const riskTotal = riskItems.reduce((sum, item) => sum + item.value, 0);
  const riskData = riskItems.map(item => ({
    ...item,
    percentage: riskTotal > 0 ? (item.value / riskTotal) * 100 : 0
  }));

  const treemapData = normalizedHoldings.map(h => ({
    name: h.ticker,
    size: h.marketValue,
    unrealized_pnl_pct: h.unrealizedPnlPct
  }));

  return (
    <div className="space-y-8 pb-12">
      <div>
        <h1 className="text-3xl font-bold tracking-tight text-white">Portfolio Insights</h1>
        <p className="text-sm text-slate-400">Deep risk analytics, valuation metrics, and asset allocations.</p>
      </div>

      <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4">
        <div className="relative overflow-hidden rounded-2xl border border-slate-800 bg-slate-900/40 p-5 shadow-sm backdrop-blur-md">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Weighted Beta</span>
            <div className="p-2 rounded-xl text-teal-400 bg-teal-500/10">
              <Activity className="h-5 w-5" />
            </div>
          </div>
          <div className="mt-3">
            <span className="text-2xl font-bold text-white tracking-tight">{weightedBeta.toFixed(2)}</span>
            <p className="text-[10px] text-slate-500 mt-1 leading-tight">
              Sensitivity to broad market. Beta &gt; 1.0 indicates high volatility; &lt; 1.0 indicates low volatility.
            </p>
          </div>
        </div>

        <div className="relative overflow-hidden rounded-2xl border border-slate-800 bg-slate-900/40 p-5 shadow-sm backdrop-blur-md">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Weighted P/E Ratio</span>
            <div className="p-2 rounded-xl text-blue-400 bg-blue-500/10">
              <TrendingUp className="h-5 w-5" />
            </div>
          </div>
          <div className="mt-3">
            <span className="text-2xl font-bold text-white tracking-tight">
              {weightedPE ? weightedPE.toFixed(1) : '—'}
            </span>
            <p className="text-[10px] text-slate-500 mt-1 leading-tight">
              Average price-to-earnings multiple of equity assets. Excludes non-equity or negative earnings.
            </p>
          </div>
        </div>

        <div className="relative overflow-hidden rounded-2xl border border-slate-800 bg-slate-900/40 p-5 shadow-sm backdrop-blur-md">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Weighted Div Yield</span>
            <div className="p-2 rounded-xl text-emerald-400 bg-emerald-500/10">
              <Percent className="h-5 w-5" />
            </div>
          </div>
          <div className="mt-3">
            <span className="text-2xl font-bold text-white tracking-tight">
              {weightedDivYield.toFixed(2)}%
            </span>
            <p className="text-[10px] text-slate-500 mt-1 leading-tight">
              Weighted dividend income output of holdings relative to current value.
            </p>
          </div>
        </div>

        <div className="relative overflow-hidden rounded-2xl border border-slate-800 bg-slate-900/40 p-5 shadow-sm backdrop-blur-md">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Weighted P/B Ratio</span>
            <div className="p-2 rounded-xl text-purple-400 bg-purple-500/10">
              <DollarSign className="h-5 w-5" />
            </div>
          </div>
          <div className="mt-3">
            <span className="text-2xl font-bold text-white tracking-tight">
              {weightedPB ? weightedPB.toFixed(2) : '—'}
            </span>
            <p className="text-[10px] text-slate-500 mt-1 leading-tight">
              Price-to-book value metric, representing market value relative to historical book value.
            </p>
          </div>
        </div>
      </div>

      <div className="rounded-2xl border border-slate-800 bg-slate-900/40 p-6 backdrop-blur-md">
        <div className="mb-4">
          <h2 className="text-lg font-bold text-white">Composition Heatmap</h2>
          <p className="text-xs text-slate-400">
            Box size represents total market value weight. Box color reflects unrealized profit (green) or loss (red).
          </p>
        </div>
        <div className="h-80 w-full overflow-hidden rounded-xl bg-slate-950/50 p-2">
          {treemapData.length > 0 ? (
            <ResponsiveContainer width="100%" height="100%">
              <Treemap
                data={treemapData}
                dataKey="size"
                content={<CustomTreemapContent />}
              />
            </ResponsiveContainer>
          ) : (
            <div className="flex items-center justify-center h-full text-slate-500 text-sm">
              No stock holdings available to display performance heatmap.
            </div>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3">
        <AllocationDonutChart
          title="Sector Allocation"
          subtitle="Breakdown of holdings by industry sector"
          data={sectorData}
          colors={COLORS}
        />

        <AllocationDonutChart
          title="Asset Class Breakdown"
          subtitle="Distribution across asset classes & cash"
          data={typeData}
          colors={COLORS}
          colorOffset={2}
        />

        <AllocationDonutChart
          title="Geographic Allocation"
          subtitle="Exposures grouped by listing country"
          data={countryData}
          colors={COLORS}
          colorOffset={4}
        />

        <AllocationDonutChart
          title="Currency Allocation"
          subtitle="Valuation distribution by native currencies"
          data={currencyData}
          colors={COLORS}
          colorOffset={1}
        />

        <AllocationDonutChart
          title="Account Distribution"
          subtitle="Asset value share per brokerage account"
          data={accountData}
          colors={COLORS}
          colorOffset={3}
        />

        <AllocationDonutChart
          title="Risk Composition"
          subtitle="Allocations categorized by Beta profile"
          data={riskData}
          colors={COLORS}
          colorOffset={5}
        />
      </div>

      <div className="rounded-2xl border border-slate-800 bg-slate-900/40 p-6 backdrop-blur-md">
        <div className="mb-6">
          <h2 className="text-lg font-bold text-white">52-Week High / Low Ranges</h2>
          <p className="text-xs text-slate-400">
            Position of the current price within each holding's historical 52-week pricing envelope.
          </p>
        </div>
        
        {normalizedHoldings.length > 0 ? (
          <div className="space-y-6">
            {normalizedHoldings.map(h => {
              const has52W = h.fifty_two_week_high && h.fifty_two_week_low && h.fifty_two_week_high > h.fifty_two_week_low;
              
              let percent = 50;
              const currentPrice = h.marketValue / h.total_shares;
              if (has52W && h.fifty_two_week_low && h.fifty_two_week_high) {
                const low = h.fifty_two_week_low;
                const high = h.fifty_two_week_high;
                percent = ((currentPrice - low) / (high - low)) * 100;
                percent = Math.max(0, Math.min(100, percent));
              }

              return (
                <div key={h.ticker} className="grid grid-cols-1 md:grid-cols-4 items-center gap-4 border-b border-slate-800/40 pb-4 last:border-0 last:pb-0">
                  <div className="md:col-span-1">
                    <p className="text-sm font-bold text-white">{h.ticker}</p>
                    <p className="text-xs text-slate-400 truncate">{h.asset_name}</p>
                  </div>
                  <div className="md:col-span-2 space-y-1.5">
                    {has52W && h.fifty_two_week_low && h.fifty_two_week_high ? (
                      <>
                        <div className="relative h-2 w-full bg-slate-800/80 rounded-full">
                          <div
                            className="absolute top-0 bottom-0 left-0 bg-gradient-to-r from-emerald-500 to-teal-400 rounded-full"
                            style={{ width: `${percent}%` }}
                          />
                          <div
                            className="absolute top-0 w-3 h-3 -mt-0.5 bg-white border border-slate-900 rounded-full shadow-md transition-all duration-200"
                            style={{ left: `calc(${percent}% - 6px)` }}
                          />
                        </div>
                        <div className="flex items-center justify-between text-[10px] text-slate-500">
                          <span>Low: {formatCurrency(h.fifty_two_week_low)}</span>
                          <span className="text-slate-300 font-medium">{percent.toFixed(0)}% from low</span>
                          <span>High: {formatCurrency(h.fifty_two_week_high)}</span>
                        </div>
                      </>
                    ) : (
                      <div className="text-xs text-slate-500 italic">52-week historical ranges not available for this asset.</div>
                    )}
                  </div>
                  <div className="md:col-span-1 text-right">
                    <p className="text-xs font-semibold text-slate-400">Current Price</p>
                    <p className="text-sm font-bold text-white">{formatCurrency(currentPrice)}</p>
                  </div>
                </div>
              );
            })}
          </div>
        ) : (
          <div className="text-center py-6 text-slate-500 text-sm">
            No holdings available to evaluate 52-week pricing ranges.
          </div>
        )}
      </div>
    </div>
  );
}
