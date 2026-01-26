import { useEffect } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { useAuthStore } from '@/store/auth.store';
import LoginPage from '@/pages/auth/LoginPage';
import StudentLayout from '@/layouts/StudentLayout';
import AdminLayout from '@/layouts/AdminLayout';
import { Toaster } from "@/components/ui/toaster"

// Student Pages
import StudentDashboard from '@/pages/student/Dashboard';
import CourseList from '@/pages/student/CourseList';
import Training from '@/pages/student/Training';
import Evaluation from '@/pages/student/Evaluation';

// Admin Pages
import AdminDashboard from '@/pages/admin/Dashboard';
import AdminCourses from '@/pages/admin/Courses';
import AdminUsers from '@/pages/admin/Users';
import AdminSettings from '@/pages/admin/Settings';

function ProtectedRoute({ children, requireAdmin = false }: { children: React.ReactNode, requireAdmin?: boolean }) {
  const { user, isLoading } = useAuthStore();
  
  if (isLoading) return <div className="flex h-screen items-center justify-center">Loading...</div>;
  if (!user) return <Navigate to="/login" replace />;
  
  // TODO: Add actual admin check here based on user metadata or role
  // if (requireAdmin && user.user_metadata.role !== 'admin') return <Navigate to="/student" replace />;
  
  return <>{children}</>;
}

export default function App() {
  const { initialize } = useAuthStore();

  useEffect(() => {
    initialize();
  }, [initialize]);

  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        
        {/* Student Routes */}
        <Route path="/student" element={
          <ProtectedRoute>
            <StudentLayout />
          </ProtectedRoute>
        }>
          <Route path="dashboard" element={<StudentDashboard />} />
          <Route path="courses" element={<CourseList />} />
          <Route path="training" element={<Training />} />
          <Route path="training/:courseId" element={<Training />} />
          <Route path="evaluation" element={<Evaluation />} />
          <Route index element={<Navigate to="dashboard" replace />} />
        </Route>

        {/* Admin Routes */}
        <Route path="/admin" element={
          <ProtectedRoute requireAdmin>
            <AdminLayout />
          </ProtectedRoute>
        }>
          <Route path="dashboard" element={<AdminDashboard />} />
          <Route path="users" element={<AdminUsers />} />
          <Route path="courses" element={<AdminCourses />} />
          <Route path="settings" element={<AdminSettings />} />
          <Route index element={<Navigate to="dashboard" replace />} />
        </Route>

        <Route path="/" element={<Navigate to="/student/dashboard" replace />} />
      </Routes>
      <Toaster />
    </BrowserRouter>
  );
}
