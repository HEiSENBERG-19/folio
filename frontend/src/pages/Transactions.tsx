import { useState } from 'react';
import { Plus, Search, Trash2, X, AlertTriangle } from 'lucide-react';
import { useTransactions, useCreateTransaction, useDeleteTransaction } from '../hooks/useTransactions';
import { useAccounts, useCreateAccount } from '../hooks/useAccounts';
import { useAssets, useCreateAsset } from '../hooks/useAssets';
import type { TxType } from '../types';

const getLocalDatetimeString = () => {
  const now = new Date();
  const tzOffset = now.getTimezoneOffset() * 60000;
  return new Date(now.getTime() - tzOffset).toISOString().slice(0, 16);
};

const formatCurrency = (val: number) => {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
  }).format(val);
};

const formatDate = (dateStr: string) => {
  const d = new Date(dateStr);
  return d.toLocaleString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
};

export default function Transactions() {
  // Filters state
  const [selectedAccountFilter, setSelectedAccountFilter] = useState<string>('');
  const [selectedAssetFilter, setSelectedAssetFilter] = useState<string>('');
  const [selectedTypeFilter, setSelectedTypeFilter] = useState<string>('');
  const [searchQuery, setSearchQuery] = useState<string>('');

  // Modal and toast state
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [toast, setToast] = useState<{ message: string; type: 'success' | 'error' } | null>(null);

  // Form fields state
  const [formAccountId, setFormAccountId] = useState<string>('');
  const [formType, setFormType] = useState<TxType>('BUY');
  const [formDate, setFormDate] = useState<string>(getLocalDatetimeString());
  const [formNotes, setFormNotes] = useState<string>('');
  const [formTicker, setFormTicker] = useState<string>('');
  const [formQuantity, setFormQuantity] = useState<string>('');
  const [formPrice, setFormPrice] = useState<string>('');
  const [formCashAmount, setFormCashAmount] = useState<string>('');

  // Inline creation states
  const [showNewAccountInput, setShowNewAccountInput] = useState(false);
  const [newAccountName, setNewAccountName] = useState('');

  // Queries & Mutations
  const { data: accounts } = useAccounts();
  const { data: assets } = useAssets();

  const filters: any = {};
  if (selectedAccountFilter) filters.account_id = Number(selectedAccountFilter);
  if (selectedAssetFilter) filters.asset_id = Number(selectedAssetFilter);
  if (selectedTypeFilter) filters.tx_type = selectedTypeFilter;

  const { data: transactions, isLoading: txsLoading } = useTransactions(filters);

  const createTransaction = useCreateTransaction();
  const deleteTransaction = useDeleteTransaction();
  const createAccount = useCreateAccount();
  const createAsset = useCreateAsset();

  const showToast = (message: string, type: 'success' | 'error') => {
    setToast({ message, type });
    setTimeout(() => {
      setToast(null);
    }, 4500);
  };

  // Maps for UI labels
  const accountsMap = (accounts || []).reduce((acc, a) => {
    if (a.id) acc[a.id] = a.name;
    return acc;
  }, {} as Record<number, string>);

  const assetsMap = (assets || []).reduce((acc, a) => {
    if (a.id) acc[a.id] = a.ticker;
    return acc;
  }, {} as Record<number, string>);

  // Client-side search filtering
  const filteredTransactions = (transactions || []).filter((tx) => {
    const ticker = tx.asset_id ? assetsMap[tx.asset_id] : '';
    const matchesSearch =
      !searchQuery ||
      tx.notes?.toLowerCase().includes(searchQuery.toLowerCase()) ||
      ticker?.toLowerCase().includes(searchQuery.toLowerCase());
    return matchesSearch;
  });

  const handleDelete = (id: number) => {
    if (window.confirm('Are you sure you want to delete this transaction? This action will recalculate your FIFO ledger positions.')) {
      deleteTransaction.mutate(id, {
        onSuccess: () => {
          showToast('Transaction deleted successfully', 'success');
        },
        onError: (err: any) => {
          const errMsg = err.response?.data?.detail || err.message || 'Failed to delete transaction';
          showToast(errMsg, 'error');
        },
      });
    }
  };

  const handleCreateAccountInline = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newAccountName.trim()) return;

    createAccount.mutate(
      { name: newAccountName.trim() },
      {
        onSuccess: (acc) => {
          setFormAccountId(String(acc.id));
          setNewAccountName('');
          setShowNewAccountInput(false);
          showToast(`Account "${acc.name}" created successfully`, 'success');
        },
        onError: (err: any) => {
          const errMsg = err.response?.data?.detail || err.message || 'Failed to create account';
          showToast(errMsg, 'error');
        },
      }
    );
  };

  const tickerUpper = formTicker.trim().toUpperCase();
  const matchedAsset = assets?.find((a) => a.ticker === tickerUpper);

  const handleRegisterAssetInline = () => {
    if (!tickerUpper) return;
    createAsset.mutate(
      { ticker: tickerUpper, name: tickerUpper },
      {
        onSuccess: (asset) => {
          showToast(`Asset ${asset.ticker} registered successfully`, 'success');
        },
        onError: (err: any) => {
          const errMsg = err.response?.data?.detail || err.message || 'Failed to register asset';
          showToast(errMsg, 'error');
        },
      }
    );
  };

  const handleFormSubmit = (e: React.FormEvent) => {
    e.preventDefault();

    if (!formAccountId) {
      showToast('Please select or create an account', 'error');
      return;
    }

    const accountIdNum = Number(formAccountId);
    const dateObj = new Date(formDate);
    const executedAtIso = dateObj.toISOString();

    const basePayload = {
      account_id: accountIdNum,
      tx_type: formType,
      notes: formNotes,
      executed_at: executedAtIso,
    };

    let payload: any = null;

    if (formType === 'BUY' || formType === 'SELL') {
      if (!matchedAsset) {
        showToast('Please register the ticker asset first', 'error');
        return;
      }
      const qty = Number(formQuantity);
      const price = Number(formPrice);

      if (isNaN(qty) || qty <= 0) {
        showToast('Quantity must be a positive number', 'error');
        return;
      }
      if (isNaN(price) || price <= 0) {
        showToast('Price must be a positive number', 'error');
        return;
      }

      payload = {
        ...basePayload,
        asset_id: matchedAsset.id,
        quantity: qty,
        price_per_unit: price,
        total_amount: qty * price,
      };
    } else {
      const amt = Number(formCashAmount);
      if (isNaN(amt) || amt <= 0) {
        showToast('Cash amount must be a positive number', 'error');
        return;
      }

      payload = {
        ...basePayload,
        asset_id: null,
        quantity: 0.0,
        price_per_unit: 0.0,
        total_amount: amt,
      };
    }

    createTransaction.mutate(payload, {
      onSuccess: () => {
        setIsModalOpen(false);
        showToast('Transaction added successfully', 'success');
        // Reset form
        setFormNotes('');
        setFormTicker('');
        setFormQuantity('');
        setFormPrice('');
        setFormCashAmount('');
        setFormDate(getLocalDatetimeString());
      },
      onError: (err: any) => {
        const errMsg = err.response?.data?.detail || err.message || 'Failed to add transaction';
        showToast(errMsg, 'error');
      },
    });
  };

  const getBadgeClass = (type: TxType) => {
    switch (type) {
      case 'BUY':
        return 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20';
      case 'SELL':
        return 'bg-red-500/10 text-red-400 border border-red-500/20';
      case 'DEPOSIT':
        return 'bg-blue-500/10 text-blue-400 border border-blue-500/20';
      case 'WITHDRAWAL':
        return 'bg-purple-500/10 text-purple-400 border border-purple-500/20';
      case 'FEE':
        return 'bg-slate-500/10 text-slate-400 border border-slate-500/20';
      default:
        return 'bg-slate-500/10 text-slate-400 border border-slate-500/20';
    }
  };

  return (
    <div className="space-y-8">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-white">Transactions</h1>
          <p className="text-sm text-slate-400">Add, track, and manage your account transactions.</p>
        </div>
        <button
          onClick={() => {
            if (accounts && accounts.length > 0 && !formAccountId) {
              setFormAccountId(String(accounts[0].id));
            }
            setIsModalOpen(true);
          }}
          className="inline-flex items-center justify-center gap-2 px-4 py-2.5 bg-gradient-to-r from-emerald-500 to-teal-500 text-slate-950 font-semibold text-sm rounded-xl hover:opacity-90 shadow-lg hover:shadow-emerald-500/10 transition-all duration-200 cursor-pointer"
        >
          <Plus className="h-5 w-5 stroke-[2.5]" />
          Add Trade
        </button>
      </div>

      {/* Filters and Search Bar */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-3 bg-slate-900/40 p-4 rounded-2xl border border-slate-800 backdrop-blur-md">
        <div className="relative md:col-span-2">
          <Search className="absolute left-3.5 top-3.5 h-4 w-4 text-slate-500" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search by ticker or notes..."
            className="w-full bg-slate-950 border border-slate-800 rounded-xl pl-11 pr-4 py-2.5 text-sm text-slate-300 placeholder-slate-500 focus:outline-none focus:border-slate-700 transition-colors"
          />
        </div>
        
        {/* Filters dropdowns */}
        <div className="flex gap-2 md:col-span-2">
          <select
            value={selectedAccountFilter}
            onChange={(e) => setSelectedAccountFilter(e.target.value)}
            className="flex-1 bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-slate-400 focus:outline-none focus:border-slate-700 transition-colors cursor-pointer"
          >
            <option value="">All Accounts</option>
            {accounts?.map((acc) => (
              <option key={acc.id} value={acc.id}>
                {acc.name}
              </option>
            ))}
          </select>

          <select
            value={selectedAssetFilter}
            onChange={(e) => setSelectedAssetFilter(e.target.value)}
            className="flex-1 bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-slate-400 focus:outline-none focus:border-slate-700 transition-colors cursor-pointer"
          >
            <option value="">All Assets</option>
            {assets?.map((asset) => (
              <option key={asset.id} value={asset.id}>
                {asset.ticker}
              </option>
            ))}
          </select>

          <select
            value={selectedTypeFilter}
            onChange={(e) => setSelectedTypeFilter(e.target.value)}
            className="flex-1 bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-slate-400 focus:outline-none focus:border-slate-700 transition-colors cursor-pointer"
          >
            <option value="">All Types</option>
            <option value="BUY">BUY</option>
            <option value="SELL">SELL</option>
            <option value="DEPOSIT">DEPOSIT</option>
            <option value="WITHDRAWAL">WITHDRAWAL</option>
            <option value="FEE">FEE</option>
          </select>
        </div>
      </div>

      {/* Transactions Table */}
      <div className="overflow-hidden rounded-2xl border border-slate-800 bg-slate-900/40 backdrop-blur-md shadow-sm">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="border-b border-slate-800 bg-slate-900/20 text-xs font-semibold uppercase tracking-wider text-slate-400">
                <th className="py-4.5 px-6">Date</th>
                <th className="py-4.5 px-6">Account</th>
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
              {txsLoading ? (
                Array.from({ length: 3 }).map((_, i) => (
                  <tr key={i} className="animate-pulse">
                    <td className="py-4 px-6"><div className="h-4 w-24 bg-slate-800 rounded" /></td>
                    <td className="py-4 px-6"><div className="h-4 w-20 bg-slate-800 rounded" /></td>
                    <td className="py-4 px-6"><div className="h-5 w-16 bg-slate-800 rounded-full" /></td>
                    <td className="py-4 px-6"><div className="h-4 w-12 bg-slate-800 rounded font-bold" /></td>
                    <td className="py-4 px-6"><div className="h-4 w-12 bg-slate-800 rounded ml-auto" /></td>
                    <td className="py-4 px-6"><div className="h-4 w-16 bg-slate-800 rounded ml-auto" /></td>
                    <td className="py-4 px-6"><div className="h-4 w-20 bg-slate-800 rounded ml-auto" /></td>
                    <td className="py-4 px-6"><div className="h-4 w-32 bg-slate-800 rounded" /></td>
                    <td className="py-4 px-6"><div className="h-8 w-8 bg-slate-800 rounded-lg mx-auto" /></td>
                  </tr>
                ))
              ) : filteredTransactions.length === 0 ? (
                <tr>
                  <td colSpan={9} className="py-12 text-center text-slate-500 font-medium">
                    No transactions found. Click "Add Trade" to record one.
                  </td>
                </tr>
              ) : (
                filteredTransactions.map((tx) => {
                  const ticker = tx.asset_id ? assetsMap[tx.asset_id] : '—';
                  const account = accountsMap[tx.account_id] || '—';
                  const isBuySell = tx.tx_type === 'BUY' || tx.tx_type === 'SELL';
                  return (
                    <tr key={tx.id} className="hover:bg-slate-900/20 transition-colors duration-150">
                      <td className="py-4 px-6 text-xs text-slate-400 whitespace-nowrap">
                        {formatDate(tx.executed_at)}
                      </td>
                      <td className="py-4 px-6 text-slate-300 font-medium whitespace-nowrap">
                        {account}
                      </td>
                      <td className="py-4 px-6 whitespace-nowrap">
                        <span className={`inline-flex px-2 py-0.5 rounded-full text-xs font-semibold ${getBadgeClass(tx.tx_type)}`}>
                          {tx.tx_type}
                        </span>
                      </td>
                      <td className="py-4 px-6 font-bold text-white whitespace-nowrap">{ticker}</td>
                      <td className="py-4 px-6 text-right font-mono whitespace-nowrap">
                        {isBuySell ? tx.quantity.toFixed(4) : '—'}
                      </td>
                      <td className="py-4 px-6 text-right font-mono whitespace-nowrap">
                        {isBuySell ? formatCurrency(tx.price_per_unit) : '—'}
                      </td>
                      <td className="py-4 px-6 text-right font-mono font-semibold text-white whitespace-nowrap">
                        {formatCurrency(tx.total_amount)}
                      </td>
                      <td className="py-4 px-6 max-w-xs truncate text-slate-400" title={tx.notes}>
                        {tx.notes || '—'}
                      </td>
                      <td className="py-4 px-6 text-center whitespace-nowrap">
                        <button
                          onClick={() => tx.id && handleDelete(tx.id)}
                          className="text-slate-500 hover:text-red-400 p-1.5 rounded-lg hover:bg-slate-950 transition-all duration-150 cursor-pointer"
                        >
                          <Trash2 className="h-4 w-4" />
                        </button>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Add Transaction Modal */}
      {isModalOpen && (
        <div className="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-lg w-full p-6 shadow-2xl space-y-4 max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <h2 className="text-xl font-bold text-white">Record Transaction</h2>
              <button
                onClick={() => setIsModalOpen(false)}
                className="text-slate-400 hover:text-slate-200 cursor-pointer"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            <form onSubmit={handleFormSubmit} className="space-y-4">
              {/* Account selection */}
              <div className="space-y-1.5">
                <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider">Account</label>
                <div className="flex gap-2">
                  {!showNewAccountInput ? (
                    <>
                      <select
                        value={formAccountId}
                        onChange={(e) => setFormAccountId(e.target.value)}
                        className="flex-1 bg-slate-950 border border-slate-800 rounded-xl px-4 py-2.5 text-sm text-slate-300 focus:outline-none focus:border-slate-700 focus:ring-1 focus:ring-slate-700 cursor-pointer"
                      >
                        <option value="" disabled>Select Account</option>
                        {accounts?.map((acc) => (
                          <option key={acc.id} value={acc.id}>
                            {acc.name} (${acc.cash_balance.toFixed(2)} cash)
                          </option>
                        ))}
                      </select>
                      <button
                        type="button"
                        onClick={() => setShowNewAccountInput(true)}
                        className="px-3 bg-slate-950 border border-slate-800 hover:border-slate-700 rounded-xl text-xs font-medium text-emerald-400 hover:text-emerald-300 transition-colors cursor-pointer"
                      >
                        + New
                      </button>
                    </>
                  ) : (
                    <div className="flex-1 flex gap-2">
                      <input
                        type="text"
                        placeholder="Account name (e.g. Robinhood)"
                        value={newAccountName}
                        onChange={(e) => setNewAccountName(e.target.value)}
                        className="flex-1 bg-slate-950 border border-slate-800 rounded-xl px-4 py-2.5 text-sm text-slate-300 focus:outline-none focus:border-slate-700 focus:ring-1 focus:ring-slate-700"
                      />
                      <button
                        type="button"
                        onClick={handleCreateAccountInline}
                        className="px-3 bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 hover:bg-emerald-500/20 rounded-xl text-xs font-bold transition-all cursor-pointer"
                      >
                        Create
                      </button>
                      <button
                        type="button"
                        onClick={() => setShowNewAccountInput(false)}
                        className="px-3 bg-slate-950 border border-slate-800 rounded-xl text-xs font-bold text-slate-400 hover:text-slate-200 cursor-pointer"
                      >
                        Cancel
                      </button>
                    </div>
                  )}
                </div>
              </div>

              {/* Transaction Type selection */}
              <div className="space-y-1.5">
                <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider">Type</label>
                <select
                  value={formType}
                  onChange={(e) => setFormType(e.target.value as TxType)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-2.5 text-sm text-slate-300 focus:outline-none focus:border-slate-700 focus:ring-1 focus:ring-slate-700 cursor-pointer"
                >
                  <option value="BUY">BUY</option>
                  <option value="SELL">SELL</option>
                  <option value="DEPOSIT">DEPOSIT</option>
                  <option value="WITHDRAWAL">WITHDRAWAL</option>
                  <option value="FEE">FEE</option>
                </select>
              </div>

              {/* Conditional rendering of inputs */}
              {formType === 'BUY' || formType === 'SELL' ? (
                <>
                  <div className="space-y-1.5">
                    <div className="flex items-center justify-between">
                      <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider">Ticker</label>
                      {formTicker && !matchedAsset && (
                        <button
                          type="button"
                          onClick={handleRegisterAssetInline}
                          className="text-xs text-emerald-400 hover:text-emerald-300 font-bold transition-colors cursor-pointer"
                        >
                          Register asset "{tickerUpper}"
                        </button>
                      )}
                    </div>
                    <input
                      type="text"
                      placeholder="e.g. AAPL"
                      value={formTicker}
                      onChange={(e) => setFormTicker(e.target.value)}
                      className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-2.5 text-sm text-slate-300 placeholder-slate-500 focus:outline-none focus:border-slate-700 focus:ring-1 focus:ring-slate-700 uppercase"
                    />
                    {formTicker && (
                      <div className="text-xs">
                        {matchedAsset ? (
                          <span className="text-emerald-400">✓ Registered: {matchedAsset.name || matchedAsset.ticker}</span>
                        ) : (
                          <span className="text-amber-400 flex items-center gap-1">
                            <AlertTriangle className="h-3.5 w-3.5 inline" />
                            Ticker not registered in system database.
                          </span>
                        )}
                      </div>
                    )}
                  </div>

                  <div className="grid grid-cols-2 gap-3">
                    <div className="space-y-1.5">
                      <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider">Quantity</label>
                      <input
                        type="number"
                        step="any"
                        placeholder="e.g. 5.5"
                        value={formQuantity}
                        onChange={(e) => setFormQuantity(e.target.value)}
                        className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-2.5 text-sm text-slate-300 placeholder-slate-500 focus:outline-none focus:border-slate-700 focus:ring-1 focus:ring-slate-700"
                      />
                    </div>
                    <div className="space-y-1.5">
                      <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider">Price per Unit ($)</label>
                      <input
                        type="number"
                        step="any"
                        placeholder="e.g. 150.25"
                        value={formPrice}
                        onChange={(e) => setFormPrice(e.target.value)}
                        className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-2.5 text-sm text-slate-300 placeholder-slate-500 focus:outline-none focus:border-slate-700 focus:ring-1 focus:ring-slate-700"
                      />
                    </div>
                  </div>

                  {formQuantity && formPrice && !isNaN(Number(formQuantity)) && !isNaN(Number(formPrice)) && (
                    <div className="text-xs text-right text-slate-400">
                      Estimated Total Cost:{' '}
                      <span className="font-semibold text-white">
                        {formatCurrency(Number(formQuantity) * Number(formPrice))}
                      </span>
                    </div>
                  )}
                </>
              ) : (
                <div className="space-y-1.5">
                  <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider">Cash Amount ($)</label>
                  <input
                    type="number"
                    step="any"
                    placeholder="e.g. 5000.00"
                    value={formCashAmount}
                    onChange={(e) => setFormCashAmount(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-2.5 text-sm text-slate-300 placeholder-slate-500 focus:outline-none focus:border-slate-700 focus:ring-1 focus:ring-slate-700"
                  />
                </div>
              )}

              {/* Execution Date selection */}
              <div className="space-y-1.5">
                <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider">Date & Time</label>
                <input
                  type="datetime-local"
                  value={formDate}
                  onChange={(e) => setFormDate(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-2.5 text-sm text-slate-300 focus:outline-none focus:border-slate-700 focus:ring-1 focus:ring-slate-700 cursor-pointer"
                />
              </div>

              {/* Notes */}
              <div className="space-y-1.5">
                <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider">Notes</label>
                <textarea
                  placeholder="Additional trade details..."
                  rows={2}
                  value={formNotes}
                  onChange={(e) => setFormNotes(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-2.5 text-sm text-slate-300 placeholder-slate-500 focus:outline-none focus:border-slate-700 focus:ring-1 focus:ring-slate-700 resize-none"
                />
              </div>

              <div className="flex gap-3 justify-end pt-3 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setIsModalOpen(false)}
                  className="px-5 py-2.5 bg-slate-950 border border-slate-800 hover:border-slate-700 rounded-xl text-sm font-semibold text-slate-400 hover:text-slate-200 transition-all duration-150 cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={createTransaction.isPending}
                  className="px-5 py-2.5 bg-gradient-to-r from-emerald-500 to-teal-500 text-slate-950 font-bold text-sm rounded-xl hover:opacity-90 shadow-lg hover:shadow-emerald-500/10 transition-all duration-200 cursor-pointer disabled:opacity-55"
                >
                  {createTransaction.isPending ? 'Saving...' : 'Submit Transaction'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Floating Toast Notification */}
      {toast && (
        <div className={`fixed bottom-5 right-5 z-50 px-5 py-3.5 rounded-xl shadow-2xl border text-sm font-semibold transition-all duration-300 animate-fade-in ${
          toast.type === 'error'
            ? 'bg-red-500/10 border-red-500/20 text-red-400'
            : 'bg-emerald-500/10 border-emerald-500/20 text-emerald-400'
        }`}>
          {toast.message}
        </div>
      )}
    </div>
  );
}
