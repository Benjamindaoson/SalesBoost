import { Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ConfigProvider } from 'antd';
import zhCN from 'antd/locale/zh_CN';
import { Layout } from './components/layout/Layout';
import { ChatPanel } from './components/chat/ChatPanel';
import { DashboardPage } from './pages/DashboardPage';
import { FlywheelPage } from './pages/FlywheelPage';
import { KnowledgePage } from './pages/KnowledgePage';
import { PromptsPage } from './pages/PromptsPage';
import { OnboardingPage } from './pages/OnboardingPage';
import Dashboard from './pages/Dashboard';
import OnboardingFlow from './pages/Onboarding';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
      staleTime: 5000,
    },
  },
});

function App() {
  return (
    <ConfigProvider locale={zhCN}>
      <QueryClientProvider client={queryClient}>
        <Routes>
          <Route path="/sales" element={<Dashboard />} />
          <Route path="/sales/onboarding" element={<OnboardingFlow />} />
          <Route element={<Layout />}>
            <Route path="/" element={<Navigate to="/sales" replace />} />
            <Route path="/chat" element={<ChatPanel />} />
            <Route path="/onboarding" element={<OnboardingPage />} />
            <Route path="/dashboard" element={<DashboardPage />} />
            <Route path="/flywheel" element={<FlywheelPage />} />
            <Route path="/knowledge" element={<KnowledgePage />} />
            <Route path="/prompts" element={<PromptsPage />} />
          </Route>
        </Routes>
      </QueryClientProvider>
    </ConfigProvider>
  );
}

export default App;
