import type { UrlStatus } from "./types";

const RENDER_BACKEND = "https://uptime-backend-0vem.onrender.com";

const RAW_BASE = import.meta.env.VITE_API_URL || "";
let API_BASE = "/api";

if (RAW_BASE) {
  API_BASE = RAW_BASE.replace(/\/$/, "").replace(/\/api$/, "");
} else if (
  typeof window !== "undefined" &&
  window.location.hostname !== "localhost" &&
  window.location.hostname !== "127.0.0.1"
) {
  API_BASE = RENDER_BACKEND;
}

console.log("[Uptime Monitor] Target API_BASE:", API_BASE);

export async function fetchStatus(): Promise<UrlStatus[]> {
  try {
    const res = await fetch(`${API_BASE}/status`);
    if (!res.ok) throw new Error(`Failed to load status (${res.status})`);
    return await res.json();
  } catch (err: any) {
    console.error("[Uptime Monitor] Error fetching status from:", `${API_BASE}/status`, err);
    throw err;
  }
}

export async function addUrl(url: string): Promise<void> {
  const res = await fetch(`${API_BASE}/urls`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ url }),
  });
  if (!res.ok) {
    const detail = await res.json().catch(() => ({}));
    throw new Error(detail.detail || `Failed to add URL (${res.status})`);
  }
}

export async function deleteUrl(id: number): Promise<void> {
  const res = await fetch(`${API_BASE}/urls/${id}`, { method: "DELETE" });
  if (!res.ok) throw new Error(`Failed to delete URL (${res.status})`);
}
