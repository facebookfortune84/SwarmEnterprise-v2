import { useEffect } from "react";
import { Navigate, Outlet, useLocation } from "react-router-dom";
import { useAuthStore } from "@/store/authStore";
import { useAuth } from "@/hooks/useAuth";

export default function ProtectedRoute() {
  const store = useAuthStore();
  const { refreshIfNeeded } = useAuth();
  const location = useLocation();

  useEffect(() => {
    void refreshIfNeeded();
  }, [refreshIfNeeded]);

  if (!store.token || store.isExpired()) {
    return (
      <Navigate
        to={`/login?redirect=${encodeURIComponent(location.pathname + location.search)}`}
        replace
      />
    );
  }

  return <Outlet />;
}
