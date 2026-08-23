import type { UrlStatus } from "./types";

// Uses VITE_API_URL if set (e.g. for Vercel deployment pointing to Render backend).
// Otherwise defaults to "/api" (for local Vite dev proxy and Nginx Docker setup).
const RAW_BASE = import.meta.env.VITE_API_URL || "";
const API_BASE = RAW_BASE ? RAW_BASE.replace(/\/$/, "") : "/api";

export async function fetchStatus(): Promise<UrlStatus[]> {
  const res = await fetch(`${API_BASE}/status`);
  if (!res.ok) throw new Error(`Failed to load status (${res.status})`);
  return res.json();
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
