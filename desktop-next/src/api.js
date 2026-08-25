const BASE = "http://127.0.0.1:8765/api/v1";

export async function api(path, options) {
  const response = await fetch(`${BASE}${path}`, options);
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(payload?.error?.message || "本機資料引擎回應失敗");
  return payload;
}

export async function fetchAllRankingPages(snapshotId, request=api) {
  const suffix=snapshotId?`&snapshot_id=${encodeURIComponent(snapshotId)}`:"";
  const first=await request(`/rankings?page=1&page_size=200${suffix}`);
  const pages=Math.max(1, Number(first.pagination?.pages) || 1);
  if (pages > 1000) throw new Error("排行榜分頁數異常，已停止載入");
  if(pages<=1)return first;
  const rest=await Promise.all(Array.from({length:pages-1},(_,index)=>request(`/rankings?page=${index+2}&page_size=200${suffix}`)));
  return {...first,items:[...(first.items||[]),...rest.flatMap((page)=>page.items||[])]};
}

export const endpoints = {
  health: () => api("/health"),
  snapshots: () => api("/snapshots"),
  rankings: (snapshotId) => fetchAllRankingPages(snapshotId),
  stock: (symbol, snapshotId) => api(`/stocks/${encodeURIComponent(symbol)}${snapshotId ? `?snapshot_id=${encodeURIComponent(snapshotId)}` : ""}`),
  metrics: (symbol, snapshotId) => api(`/stocks/${encodeURIComponent(symbol)}/metrics${snapshotId ? `?snapshot_id=${encodeURIComponent(snapshotId)}` : ""}`),
  financials: (symbol) => api(`/stocks/${encodeURIComponent(symbol)}/financials`),
  history: (symbol) => api(`/stocks/${encodeURIComponent(symbol)}/rank-history`),
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
