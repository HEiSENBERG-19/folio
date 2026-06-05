import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer } from 'recharts';
import { useCurrency } from '../../context/CurrencyContext';

interface AllocationItem {
  name: string;
  value: number;
  percentage: number;
  color?: string;
}

interface CustomTooltipProps {
  active?: boolean;
  payload?: Array<{
    payload: {
      name: string;
      value: number;
      percentage: number;
    };
  }>;
  formatCurrency: (value: number | null | undefined) => string;
}

const CustomTooltip = ({ active, payload, formatCurrency }: CustomTooltipProps) => {
  if (active && payload && payload.length) {
    const d = payload[0].payload;
    return (
      <div className="bg-slate-900 border border-slate-800 p-3 rounded-xl shadow-lg backdrop-blur-md">
        <p className="text-xs font-semibold text-slate-400">{d.name}</p>
        <p className="text-sm font-bold text-white mt-1">Value: {formatCurrency(d.value)}</p>
        <p className="text-xs font-semibold text-emerald-400">Share: {d.percentage.toFixed(2)}%</p>
      </div>
    );
  }
  return null;
};

interface Props {
  title: string;
  subtitle: string;
  data: AllocationItem[];
  colors: string[];
  colorOffset?: number;
  maxLegendItems?: number;
}

export default function AllocationDonutChart({
  title, subtitle, data, colors, colorOffset = 0, maxLegendItems = 4,
}: Props) {
  const { formatCurrency } = useCurrency();

  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-900/40 p-6 backdrop-blur-md flex flex-col justify-between h-[360px]">
      <div>
        <h2 className="text-base font-bold text-white">{title}</h2>
        <p className="text-xs text-slate-500">{subtitle}</p>
      </div>
      <div className="h-48 my-2 relative">
        {data.length > 0 ? (
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie data={data} cx="50%" cy="50%" innerRadius={50} outerRadius={70} paddingAngle={2} dataKey="value">
                {data.map((d, index) => (
                  <Cell key={`cell-${index}`} fill={d.color || colors[(index + colorOffset) % colors.length]} />
                ))}
              </Pie>
              <Tooltip content={<CustomTooltip formatCurrency={formatCurrency} />} />
            </PieChart>
          </ResponsiveContainer>
        ) : (
          <div className="flex items-center justify-center h-full text-slate-500 text-xs">No data available</div>
        )}
      </div>
      <div className="text-xs text-slate-400 flex items-center justify-center gap-1.5 flex-wrap overflow-y-auto max-h-12">
        {data.slice(0, maxLegendItems).map((d, index) => (
          <span key={d.name} className="inline-flex items-center gap-1">
            <span className="w-2 h-2 rounded-full" style={{ backgroundColor: d.color || colors[(index + colorOffset) % colors.length] }} />
            <span>{d.name} ({d.percentage.toFixed(0)}%)</span>
          </span>
        ))}
        {data.length > maxLegendItems && <span>+ {data.length - maxLegendItems} more</span>}
      </div>
    </div>
  );
}
