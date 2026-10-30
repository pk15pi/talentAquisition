import axios, { type AxiosError, type InternalAxiosRequestConfig } from "axios";

const baseURL = import.meta.env.VITE_API_URL || "http://localhost:8000/api/v1";
const api = axios.create({ baseURL });

type RetryConfig = InternalAxiosRequestConfig & { _retry?: boolean };

api.interceptors.request.use((config) => {
  const token = localStorage.getItem("access");
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

let refreshRequest: Promise<string | null> | null = null;

export function logout() {
  localStorage.removeItem("access");
  localStorage.removeItem("refresh");
}

function redirectToLogin() {
  if (typeof window !== "undefined" && !window.location.pathname.startsWith("/login")) {
    window.location.assign("/login");
  }
}

async function refreshAccessToken(): Promise<string | null> {
  const refresh = localStorage.getItem("refresh");
  if (!refresh) return null;
  const { data } = await axios.post(`${baseURL}/auth/token/refresh/`, { refresh });
  localStorage.setItem("access", data.access);
  return data.access as string;
}

api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const original = error.config as RetryConfig | undefined;
    const url = original?.url || "";
    const isAuthCall = url.includes("/auth/token/");
    if (!original || error.response?.status !== 401 || original._retry || isAuthCall) {
      return Promise.reject(error);
    }
    original._retry = true;
    try {
      if (!refreshRequest) {
        refreshRequest = refreshAccessToken().finally(() => {
          refreshRequest = null;
        });
      }
      const access = await refreshRequest;
      if (!access) {
        logout();
        redirectToLogin();
        return Promise.reject(error);
      }
      original.headers.Authorization = `Bearer ${access}`;
      return api(original);
    } catch (refreshError) {
      logout();
      redirectToLogin();
      return Promise.reject(refreshError);
    }
  },
);

export async function login(username: string, password: string) {
  const { data } = await api.post("/auth/token/", { username, password });
  localStorage.setItem("access", data.access);
  localStorage.setItem("refresh", data.refresh);
  return data;
}

export default api;
