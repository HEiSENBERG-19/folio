export type TxType = "BUY" | "SELL" | "DEPOSIT" | "WITHDRAWAL" | "FEE";

export interface Account {
  id?: number;
  name: string;
  cash_balance: number;
  currency: string;
  created_at?: string;
  updated_at?: string;
}

export interface Asset {
  id?: number;
  ticker: string;
  name: string;
  created_at?: string;
}

export interface Transaction {
  id?: number;
  account_id: number;
  asset_id?: number | null;
  tx_type: TxType;
  quantity: number;
  price_per_unit: number;
  total_amount: number;
  notes: string;
  executed_at: string;
  created_at?: string;
}

export interface HoldingDetail {
  ticker: string;
  asset_name: string;
  total_shares: number;
  avg_cost_basis: number;
  current_price: number;
  market_value: number;
  unrealized_pnl: number;
  unrealized_pnl_pct: number;
  realized_pnl: number;
}

export interface PortfolioSummary {
  total_invested: number;
  total_market_value: number;
  total_cash: number;
  total_realized_pnl: number;
  total_unrealized_pnl: number;
  net_portfolio_value: number;
  holdings: HoldingDetail[];
}

export interface PortfolioHistoryPoint {
  date: string;
  portfolio_value: number;
  cash_balance: number;
  total_value: number;
}

export interface PortfolioHistory {
  period: string;
  data_points: PortfolioHistoryPoint[];
}

export interface AllocationSlice {
  ticker: string;
  market_value: number;
  percentage: number;
}

export interface HoldingInsightDetail {
  ticker: string;
  asset_name: string;
  total_shares: number;
  market_value_native: number;
  currency: string;
  asset_class: string;
  sector?: string | null;
  industry?: string | null;
  country?: string | null;
  exchange?: string | null;
  beta?: number | null;
  market_cap?: number | null;
  fifty_two_week_high?: number | null;
  fifty_two_week_low?: number | null;
  trailing_pe?: number | null;
  dividend_yield?: number | null;
  price_to_book?: number | null;
  unrealized_pnl_native: number;
}

export interface CashInsightDetail {
  account_id: number;
  account_name: string;
  cash_balance_native: number;
  currency: string;
  stock_value_native: number;
}

export interface PortfolioInsights {
  holdings: HoldingInsightDetail[];
  cash_balances: CashInsightDetail[];
}

export interface CsvImportResult {
  total_rows: number;
  imported_count: number;
  skipped_count: number;
  errors: Array<{ row: number; message: string }>;
  created_accounts: string[];
  created_assets: string[];
}

