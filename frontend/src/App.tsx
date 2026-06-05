import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';

import AppShell from './components/layout/AppShell';
import Dashboard from './pages/Dashboard';
import Holdings from './pages/Holdings';
import Transactions from './pages/Transactions';
import Insights from './pages/Insights';
import { CurrencyProvider } from './context/CurrencyContext';

export default function App() {
  return (
    <CurrencyProvider>
      <Router>
        <AppShell>
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/holdings" element={<Holdings />} />
            <Route path="/transactions" element={<Transactions />} />
            <Route path="/insights" element={<Insights />} />
          </Routes>
        </AppShell>
      </Router>
    </CurrencyProvider>
  );
}

