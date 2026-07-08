import type { UrlStatus } from "../types";
import { deleteUrl } from "../api";

interface Props {
  rows: UrlStatus[];
  onChanged: () => void;
}

function StatusBadge({ isUp }: { isUp: boolean | null }) {
  if (isUp === null) {
    return (
      <span className="inline-flex items-center gap-1.5 rounded-full bg-slate-100 px-2.5 py-1 text-xs font-medium text-slate-600">
        <span className="h-2 w-2 rounded-full bg-slate-400" />
        Pending
      </span>
    );
  }
  return isUp ? (
    <span className="inline-flex items-center gap-1.5 rounded-full bg-green-100 px-2.5 py-1 text-xs font-medium text-green-700">
      <span className="h-2 w-2 rounded-full bg-green-500" />
      Up
    </span>
  ) : (
    <span className="inline-flex items-center gap-1.5 rounded-full bg-red-100 px-2.5 py-1 text-xs font-medium text-red-700">
      <span className="h-2 w-2 rounded-full bg-red-500" />
      Down
    </span>
  );
}

function formatTime(iso: string | null): string {
  if (!iso) return "—";
  // Backend stores naive UTC; append Z so the browser renders local time.
  const d = new Date(iso.endsWith("Z") ? iso : iso + "Z");
  return d.toLocaleTimeString();
}

export default function StatusTable({ rows, onChanged }: Props) {
  async function handleDelete(id: number) {
    await deleteUrl(id);
    onChanged();
  }

  if (rows.length === 0) {
    return (
      <div className="rounded-lg border border-dashed border-slate-300 p-10 text-center text-sm text-slate-500">
        No URLs monitored yet. Add one above to get started.
      </div>
    );
  }

  return (
    <div className="overflow-hidden rounded-lg border border-slate-200">
      <table className="w-full text-left text-sm">
        <thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
          <tr>
            <th className="px-4 py-3">URL</th>
            <th className="px-4 py-3">Status</th>
            <th className="px-4 py-3">Code</th>
            <th className="px-4 py-3">Response</th>
            <th className="px-4 py-3">Last checked</th>
            <th className="px-4 py-3"></th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100">
          {rows.map((row) => (
            <tr key={row.id} className="hover:bg-slate-50">
              <td className="max-w-xs truncate px-4 py-3 font-medium text-slate-800">
                {row.url}
              </td>
              <td className="px-4 py-3">
                <StatusBadge isUp={row.is_up} />
              </td>
              <td className="px-4 py-3 text-slate-600">
                {row.status_code ?? "—"}
              </td>
              <td className="px-4 py-3 text-slate-600">
                {row.response_time_ms != null
                  ? `${Math.round(row.response_time_ms)} ms`
                  : "—"}
              </td>
              <td className="px-4 py-3 text-slate-500">
                {formatTime(row.last_checked)}
              </td>
              <td className="px-4 py-3 text-right">
                <button
                  onClick={() => handleDelete(row.id)}
                  className="text-xs text-slate-400 transition hover:text-red-600"
                >
                  Remove
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
