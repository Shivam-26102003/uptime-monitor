import type { UrlStatus } from "./types";

// Same-origin "/api" prefix. In dev, Vite proxies it to the backend; in the
// Docker build, nginx proxies it. Either way the browser never needs to know
// the backend's real host, which sidesteps the "http://backend:8000 from the
// browser" trap (see AI_LOG.md).
const API_BASE = "/api";

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
