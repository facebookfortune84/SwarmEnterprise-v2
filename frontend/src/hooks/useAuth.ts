import { useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { useAuthStore } from "@/store/authStore";
import ApiClient from "@/services/ApiClient";
import toast from "react-hot-toast";

export function useAuth() {
  const store = useAuthStore();
  const navigate = useNavigate();

  const login = useCallback(
    async (emailOrPayload: string | { email: string; password: string }, password?: string) => {
      const payload =
        typeof emailOrPayload === "string"
          ? { email: emailOrPayload, password: password ?? "" }
          : emailOrPayload;
      const data = await ApiClient.auth.login(payload);
      store.setToken(data.access_token);
      toast.success("Welcome back!");
      const params = new URLSearchParams(window.location.search);
      const redirect = params.get("redirect") ?? "/";
      navigate(redirect, { replace: true });
      return data;
    },
    [store, navigate],
  );

  const register = useCallback(
    async (
      emailOrPayload: string | { email: string; password: string; full_name: string },
      password?: string,
      fullName?: string,
    ) => {
      const payload =
        typeof emailOrPayload === "string"
          ? { email: emailOrPayload, password: password ?? "", full_name: fullName ?? "" }
          : emailOrPayload;
      const data = await ApiClient.auth.register(payload);
      store.setToken(data.access_token);
      toast.success("Account created — welcome!");
      navigate("/", { replace: true });
      return data;
    },
    [store, navigate],
  );

  const logout = useCallback(async () => {
    try {
      await ApiClient.auth.logout();
    } catch {
      // ignore logout errors
    }
    store.clearToken();
    navigate("/login", { replace: true });
    toast("Signed out.");
  }, [store, navigate]);

  const refreshIfNeeded = useCallback(async () => {
    if (!store.isNearExpiry()) return;
    const refreshToken = localStorage.getItem("refresh_token");
    if (!refreshToken) {
      store.clearToken();
      navigate("/login?redirect=" + encodeURIComponent(window.location.pathname), {
        replace: true,
      });
      return;
    }
    try {
      const data = await ApiClient.auth.refresh(refreshToken);
      store.setToken(data.access_token);
    } catch {
      store.clearToken();
      setTimeout(() => {
        navigate("/login?redirect=" + encodeURIComponent(window.location.pathname), {
          replace: true,
        });
      }, 500);
    }
  }, [store, navigate]);

  return {
    token: store.token,
    isAuthenticated: () => !!store.token && !store.isExpired(),
    isAdmin: () => {
      const decoded = store.getDecodedToken();
      return decoded?.role === "admin";
    },
    login,
    register,
    logout,
    refreshIfNeeded,
  };
}
