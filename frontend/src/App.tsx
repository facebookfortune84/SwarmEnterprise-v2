import { Suspense, lazy } from "react";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Toaster } from "react-hot-toast";
import ProtectedRoute from "@/components/ProtectedRoute";

// Lazy-loaded pages (route-based code splitting)
const Login = lazy(() => import("@/pages/login"));
const Register = lazy(() => import("@/pages/register"));
const Dashboard = lazy(() => import("@/pages/dashboard"));
const Profile = lazy(() => import("@/pages/profile"));
const Admin = lazy(() => import("@/pages/admin"));
const Companies = lazy(() => import("@/pages/companies/index"));
const CompanyDetail = lazy(() => import("@/pages/companies/[id]"));
const Deployments = lazy(() => import("@/pages/deployments"));
const Tenants = lazy(() => import("@/pages/tenants"));
const Tickets = lazy(() => import("@/pages/tickets"));
const Analytics = lazy(() => import("@/pages/analytics"));
const Leads = lazy(() => import("@/pages/leads"));
const Outreach = lazy(() => import("@/pages/outreach/index"));
const WorkflowList = lazy(() => import("@/pages/workflows/index"));
const WorkflowBuilder = lazy(() => import("@/pages/workflows/builder"));

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      staleTime: 30_000,
    },
  },
});

function LoadingSpinner() {
  return (
    <div className="flex items-center justify-center min-h-screen bg-neutral-950">
      <div className="w-8 h-8 border-2 border-brand-500 border-t-transparent rounded-full animate-spin" />
    </div>
  );
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Toaster
          position="top-right"
          toastOptions={{
            duration: 8000,
            style: {
              background: "#1f2937",
              color: "#f9fafb",
              border: "1px solid #374151",
            },
          }}
        />
        <Suspense fallback={<LoadingSpinner />}>
          <Routes>
            {/* Public routes */}
            <Route path="/login" element={<Login />} />
            <Route path="/register" element={<Register />} />

            {/* Protected routes */}
            <Route element={<ProtectedRoute />}>
              <Route path="/" element={<Dashboard />} />
              <Route path="/dashboard" element={<Dashboard />} />
              <Route path="/profile" element={<Profile />} />
              <Route path="/admin" element={<Admin />} />
              <Route path="/companies" element={<Companies />} />
              <Route path="/companies/:id" element={<CompanyDetail />} />
              <Route path="/deployments" element={<Deployments />} />
              <Route path="/tenants" element={<Tenants />} />
              <Route path="/tickets" element={<Tickets />} />
              <Route path="/analytics" element={<Analytics />} />
              <Route path="/leads" element={<Leads />} />
              <Route path="/outreach/*" element={<Outreach />} />
              <Route path="/workflows" element={<WorkflowList />} />
              <Route path="/workflows/builder" element={<WorkflowBuilder />} />
            </Route>

            {/* Catch-all */}
            <Route
              path="*"
              element={
                <div className="flex flex-col items-center justify-center min-h-screen text-neutral-400">
                  <h1 className="text-3xl font-bold text-white mb-2">404</h1>
                  <p>Page not found.</p>
                  <a href="/" className="mt-4 text-brand-400 hover:underline">
                    Go home
                  </a>
                </div>
              }
            />
          </Routes>
        </Suspense>
      </BrowserRouter>
    </QueryClientProvider>
  );
}
