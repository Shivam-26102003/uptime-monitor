import type { UrlStatus } from "./types";

const API_BASE = import.meta.env.VITE_API_URL || "/api";

export async function fetchStatus(): Promise<UrlStatus[]> {
  const res = await fetch(`${API_BASE}/status`);
  if (!res.ok) {
    throw new Error(`Failed to load status (${res.status})`);
  }
  return await res.json();
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
  const res = await fetch(`${API_BASE}/urls/${id}`, {
    method: "DELETE",
  });
  if (!res.ok) {
    throw new Error(`Failed to delete URL (${res.status})`);
  }
}
