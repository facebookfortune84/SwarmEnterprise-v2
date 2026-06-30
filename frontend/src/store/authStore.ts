import { create } from "zustand";
import { jwtDecode } from "jwt-decode";
import type { DecodedToken } from "@/types/api";

interface AuthState {
  token: string | null;
  setToken: (token: string) => void;
  clearToken: () => void;
  getDecodedToken: () => DecodedToken | null;
  isExpired: () => boolean;
  isNearExpiry: () => boolean;
}

const TOKEN_KEY = "auth_token";

export const useAuthStore = create<AuthState>()((set, get) => ({
  token: localStorage.getItem(TOKEN_KEY),

  setToken: (token: string) => {
    localStorage.setItem(TOKEN_KEY, token);
    set({ token });
  },

  clearToken: () => {
    localStorage.removeItem(TOKEN_KEY);
    set({ token: null });
  },

  getDecodedToken: (): DecodedToken | null => {
    const { token } = get();
    if (!token) return null;
    try {
      return jwtDecode<DecodedToken>(token);
    } catch {
      return null;
    }
  },

  isExpired: (): boolean => {
    const decoded = get().getDecodedToken();
    if (!decoded) return true;
    return decoded.exp * 1000 < Date.now();
  },

  isNearExpiry: (): boolean => {
    const decoded = get().getDecodedToken();
    if (!decoded) return true;
    // True when exp < now + 60 seconds
    return decoded.exp * 1000 < Date.now() + 60_000;
  },
}));
