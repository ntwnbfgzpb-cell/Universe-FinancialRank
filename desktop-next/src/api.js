const BASE = "http://127.0.0.1:8765/api/v1";

export async function api(path, options) {
  const response = await fetch(`${BASE}${path}`, options);
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(payload?.error?.message || "本機資料引擎回應失敗");
  return payload;
}

export const endpoints = {
  health: () => api("/health"),
  snapshots: () => api("/snapshots"),
  rankings: (snapshotId) => api(`/rankings?page=1&page_size=200${snapshotId ? `&snapshot_id=${snapshotId}` : ""}`),
  stock: (symbol, snapshotId) => api(`/stocks/${symbol}${snapshotId ? `?snapshot_id=${snapshotId}` : ""}`),
  metrics: (symbol, snapshotId) => api(`/stocks/${symbol}/metrics${snapshotId ? `?snapshot_id=${snapshotId}` : ""}`),
  financials: (symbol) => api(`/stocks/${symbol}/financials`),
  history: (symbol) => api(`/stocks/${symbol}/rank-history`),
  quality: () => api("/admin/data-quality"),
  rules: () => api("/rules"),
  sources: () => api("/admin/sources"),
  syncStatus: () => api("/admin/sync"),
  sync: (status = "PROVISIONAL") => api("/admin/sync", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ status }) }),
  backups: () => api("/admin/backups"),
  createBackup: () => api("/admin/backups", { method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify({action:"create"}) }),
  restoreBackup: (backupId) => api("/admin/backups", { method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify({action:"restore",backup_id:backupId,confirmation:"RESTORE"}) }),
};

export function rankingCsvUrl(snapshotId) {
  return `${BASE}/export/rankings.csv${snapshotId ? `?snapshot_id=${snapshotId}` : ""}`;
}
