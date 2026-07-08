import { useCallback, useEffect, useRef, useState } from "react";
import AddUrlForm from "./components/AddUrlForm";
import StatusTable from "./components/StatusTable";
import { fetchStatus } from "./api";
import type { UrlStatus } from "./types";

const REFRESH_MS = 10_000;

export default function App() {
  const [rows, setRows] = useState<UrlStatus[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [lastRefresh, setLastRefresh] = useState<Date | null>(null);

  const load = useCallback(async () => {
    try {
      const data = await fetchStatus();
      setRows(data);
      setLastRefresh(new Date());
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load");
    }
  }, []);

  // Keep the interval pointed at the latest `load` without resetting the timer
  // on every render (the classic stale-closure interval bug — see AI_LOG.md).
  const loadRef = useRef(load);
  loadRef.current = load;

  useEffect(() => {
    loadRef.current();
    const id = setInterval(() => loadRef.current(), REFRESH_MS);
    return () => clearInterval(id);
  }, []);

  const upCount = rows.filter((r) => r.is_up === true).length;
  const downCount = rows.filter((r) => r.is_up === false).length;

  return (
    <div className="min-h-screen bg-slate-100 py-10">
      <div className="mx-auto max-w-4xl px-4">
        <header className="mb-8">
          <h1 className="text-2xl font-bold text-slate-900">Uptime Monitor</h1>
          <p className="mt-1 text-sm text-slate-500">
            {rows.length} monitored · {upCount} up · {downCount} down
            {lastRefresh && (
              <span className="ml-2 text-slate-400">
                (refreshed {lastRefresh.toLocaleTimeString()})
              </span>
            )}
          </p>
        </header>

        <AddUrlForm onAdded={load} />

        {error && (
          <div className="mb-4 rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700">
            {error}
          </div>
        )}

        <StatusTable rows={rows} onChanged={load} />

        <p className="mt-6 text-center text-xs text-slate-400">
          Auto-refreshes every 10 seconds · backend checks every 60 seconds
        </p>
      </div>
    </div>
  );
}
