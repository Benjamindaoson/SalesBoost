import { createBrowserRouter, RouterProvider, Navigate } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import Layout from "./components/layout/Layout";
import DashboardPage from "./pages/Dashboard/DashboardPage";
import PersonaPage from "./pages/Persona/PersonaPage";
import HistoryPage from "./pages/History/HistoryPage";
import PracticeRoomPage from "./pages/PracticeRoom";

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
