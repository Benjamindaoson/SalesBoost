import { useEffect, lazy, Suspense } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { useAuthStore } from '@/store/auth.store';
import ErrorBoundary from '@/components/common/ErrorBoundary';
import SecurityBanner from '@/components/common/SecurityBanner';
import { Toaster } from "@/components/ui/toaster"

// Eager load login page (critical path)
import LoginPage from '@/pages/auth/LoginPage';

// Lazy load layouts
const StudentLayout = lazy(() => import('@/layouts/StudentLayout'));
const AdminLayout = lazy(() => import('@/layouts/AdminLayout'));

// Lazy load student pages
const StudentDashboard = lazy(() => import('@/pages/student/Dashboard'));
const CustomerList = lazy(() => import('@/pages/student/CustomerList'));
const History = lazy(() => import('@/pages/student/History'));
const CourseList = lazy(() => import('@/pages/student/CourseList'));
const Training = lazy(() => import('@/pages/student/Training'));
const Evaluation = lazy(() => import('@/pages/student/Evaluation'));
const BattleCenter = lazy(() => import('@/pages/student/BattleCenter'));
const Pipeline = lazy(() => import('@/pages/student/Pipeline'));
const BattlePrep = lazy(() => import('@/pages/student/BattlePrep'));
const Review = lazy(() => import('@/pages/student/Review'));
const LiveAssist = lazy(() => import('@/pages/student/LiveAssist'));

// Lazy load admin pages
const AdminDashboard = lazy(() => import('@/pages/Admin/Dashboard'));
const AdminCourses = lazy(() => import('@/pages/Admin/Courses'));
const AdminTasks = lazy(() => import('@/pages/Admin/Tasks'));
const AdminAnalysis = lazy(() => import('@/pages/Admin/Analysis'));
const AdminUsers = lazy(() => import('@/pages/Admin/Users'));
const AdminSettings = lazy(() => import('@/pages/Admin/Settings'));
const EvolutionTrends = lazy(() => import('@/pages/Admin/EvolutionTrends'));
const KnowledgeBase = lazy(() => import('@/pages/Admin/KnowledgeBase'));
const Cockpit = lazy(() => import('@/pages/Admin/Cockpit'));

// Loading fallback component
function LoadingFallback() {
  return (
    <div className="flex h-screen items-center justify-center">
      <div className="text-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-gray-900 mx-auto mb-4"></div>
        <p className="text-gray-600">Loading...</p>
      </div>
    </div>
  );
}

function ProtectedRoute({ children, requireAdmin = false }: { children: React.ReactNode, requireAdmin?: boolean }) {
  const { user, isLoading } = useAuthStore();

  if (isLoading) {
    return <LoadingFallback />;
  }

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  // Admin role check - verify user has admin role in metadata
  if (requireAdmin) {
    const userRole = user.user_metadata?.role || user.app_metadata?.role;

    if (userRole !== 'admin') {
      console.warn('Access denied: User does not have admin role', { userId: user.id, role: userRole });
      return <Navigate to="/student/dashboard" replace />;
    }
  }

  return <>{children}</>;
}

export default function App() {
  const { initialize } = useAuthStore();

  useEffect(() => {
    initialize();
  }, [initialize]);

  return (
    <ErrorBoundary>
      <SecurityBanner />
      <BrowserRouter>
        <Suspense fallback={<LoadingFallback />}>
          <Routes>
            <Route path="/login" element={<LoginPage />} />

            {/* Sales Battle System Routes */}
            <Route path="/student" element={<StudentLayout />}>
              <Route path="battle-center" element={<BattleCenter />} />
              <Route path="pipeline" element={<Pipeline />} />
              <Route path="battle-prep/:dealId" element={<BattlePrep />} />
              <Route path="live-assist" element={<LiveAssist />} />
              <Route path="review" element={<Review />} />
              <Route path="training" element={<Training />} />
              <Route path="training/:courseId" element={<Training />} />
              {/* Legacy routes */}
              <Route path="dashboard" element={<BattleCenter />} />
              <Route path="customers" element={<CustomerList />} />
              <Route path="history" element={<History />} />
              <Route path="courses" element={<CourseList />} />
              <Route path="evaluation" element={<Evaluation />} />
              <Route index element={<Navigate to="battle-center" replace />} />
            </Route>

            {/* Admin Routes */}
            <Route path="/admin" element={
              <ProtectedRoute requireAdmin>
                <AdminLayout />
              </ProtectedRoute>
            }>
              <Route path="cockpit" element={<Cockpit />} />
              <Route path="dashboard" element={<AdminDashboard />} />
              <Route path="users" element={<AdminUsers />} />
              <Route path="courses" element={<AdminCourses />} />
              <Route path="tasks" element={<AdminTasks />} />
              <Route path="analysis" element={<AdminAnalysis />} />
              <Route path="knowledge" element={<KnowledgeBase />} />
              <Route path="evolution" element={<EvolutionTrends />} />
              <Route path="settings" element={<AdminSettings />} />
              <Route index element={<Navigate to="cockpit" replace />} />
            </Route>

            <Route path="/" element={<Navigate to="/student/battle-center" replace />} />
          </Routes>
        </Suspense>
        <Toaster />
      </BrowserRouter>
    </ErrorBoundary>
  );
}
