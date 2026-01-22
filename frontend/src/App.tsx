import { createBrowserRouter, RouterProvider, Navigate } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import Layout from "./components/layout/Layout";
import AdminLayout from "./components/layout/AdminLayout";
import DashboardPage from "./pages/Dashboard/DashboardPage";
import PersonaPage from "./pages/Persona/PersonaPage";
import HistoryPage from "./pages/History/HistoryPage";
import PracticeRoomPage from "./pages/PracticeRoom";
import LoginPage from "./pages/Login/LoginPage";

// Admin Pages
import AdminDashboard from "./pages/Admin/Dashboard";
import AdminCourses from "./pages/Admin/Courses";
import AdminPersonas from "./pages/Admin/Personas";
import AdminEvaluation from "./pages/Admin/Evaluation";
import AdminKnowledge from "./pages/Admin/Knowledge";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60 * 1000,
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});

const router = createBrowserRouter([
  {
    path: "/login",
    element: <LoginPage />,
  },
  {
    path: "/",
    element: <Layout />,
    children: [
      {
        index: true,
        element: <Navigate to="/dashboard" replace />,
      },
      {
        path: "dashboard",
        element: <DashboardPage />,
      },
      {
        path: "persona",
        element: <PersonaPage />,
      },
      {
        path: "history",
        element: <HistoryPage />,
      },
      {
        path: "practice/:sessionId",
        element: <PracticeRoomPage />,
      },
    ],
  },
  {
    path: "/admin",
    element: <AdminLayout />,
    children: [
      {
        index: true,
        element: <Navigate to="/admin/dashboard" replace />,
      },
      {
        path: "dashboard",
        element: <AdminDashboard />,
      },
      {
        path: "courses",
        element: <AdminCourses />,
      },
      {
        path: "personas",
        element: <AdminPersonas />,
      },
      {
        path: "evaluation",
        element: <AdminEvaluation />,
      },
      {
        path: "knowledge",
        element: <AdminKnowledge />,
      },
    ],
  },
  {
    path: "*",
    element: <Navigate to="/dashboard" replace />,
  }
]);

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>
  );
}

export default App;
