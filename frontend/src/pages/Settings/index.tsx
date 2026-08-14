import { useState } from "react";
import { AlertTriangle, CheckCircle2, Database, HardDrive, LoaderCircle, RefreshCw, ShieldCheck, Trash2 } from "lucide-react";

import { useBackupProtection, useBackups, useCreateBackup, useDeleteBackup, useRestoreBackup, useUpdateBackupProtection, useVerifyBackup, useWorkspaceInfo } from "@/features/workspace/hooks";
import type { BackupItem } from "@/features/workspace/types";

function formatBytes(value: number) {
  if (value < 1024 * 1024) return `${Math.round(value / 1024)} KB`;
  return `${(value / (1024 * 1024)).toFixed(1)} MB`;
}

function formatDate(value: string | null) {
  return value ? new Intl.DateTimeFormat("zh-CN", { dateStyle: "medium", timeStyle: "short" }).format(new Date(value)) : "尚无成功备份";
}

export default function Settings() {
  const workspace = useWorkspaceInfo();
  const backups = useBackups();
  const createBackup = useCreateBackup();
  const verifyBackup = useVerifyBackup();
  const deleteBackup = useDeleteBackup();
  const restoreBackup = useRestoreBackup();
  const protection = useBackupProtection();
  const updateProtection = useUpdateBackupProtection();
  const [message, setMessage] = useState<string | null>(null);
  const [restoreTarget, setRestoreTarget] = useState<BackupItem | null>(null);

  const handleCreate = async () => {
    setMessage(null);
    try {
      const backup = await createBackup.mutateAsync();
      setMessage(`备份完成并已校验：${backup.filename}`);
    } catch {
      setMessage("创建备份失败，请查看后端日志后重试。");
    }
  };

  const handleVerify = async (backup: BackupItem) => {
    setMessage(null);
    try {
      const result = await verifyBackup.mutateAsync(backup.backup_id);
      setMessage(result.valid ? `备份校验通过：${backup.filename}` : `备份校验失败：${result.errors.join("；")}`);
    } catch {
      setMessage("无法校验该备份。");
    }
  };

  const handleProtectionUpdate = async (update: { enabled?: boolean; frequency?: "daily" | "weekly"; retention?: number }) => {
    setMessage(null);
    try {
      await updateProtection.mutateAsync(update);
      setMessage("自动备份策略已保存。");
    } catch {
      setMessage("无法保存自动备份策略，请稍后重试。");
    }
  };

  const handleRestore = async () => {
    if (!restoreTarget) return;
    setMessage(null);
    try {
      await restoreBackup.mutateAsync(restoreTarget.backup_id);
      window.location.assign("/");
    } catch {
      setMessage("恢复失败；系统已尝试自动回退到恢复前状态。请查看后端日志。");
      setRestoreTarget(null);
    }
  };

  return (
    <div className="mx-auto max-w-4xl p-6">
      <div className="mb-6">
        <h1 className="text-xl font-semibold text-gray-900 dark:text-gray-100">数据与存储</h1>
        <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">运行数据保存在本地 Workspace；备份以可验证的 .airw 归档保存。</p>
      </div>

      {message && <div className="mb-4 rounded-lg border border-primary-200 bg-primary-50 px-4 py-3 text-sm text-primary-800 dark:border-primary-900 dark:bg-primary-950 dark:text-primary-200">{message}</div>}

      <section className="card mb-4">
        <div className="mb-4 flex items-center gap-2"><HardDrive className="h-4 w-4 text-primary-500" /><h2 className="text-sm font-semibold">工作区</h2></div>
        {workspace.isLoading ? <p className="text-sm text-gray-500">正在读取工作区信息…</p> : workspace.data ? (
          <div className="grid gap-4 text-sm md:grid-cols-2">
            <div><p className="text-gray-500">数据目录</p><p className="mt-1 break-all font-medium">{workspace.data.workspace_path}</p></div>
            <div><p className="text-gray-500">备份目录</p><p className="mt-1 break-all font-medium">{workspace.data.backup_path}</p></div>
            <div><p className="text-gray-500">数据库 / 文件存储</p><p className="mt-1 font-medium">{formatBytes(workspace.data.database_bytes)} / {formatBytes(workspace.data.storage_bytes)}</p></div>
            <div><p className="text-gray-500">论文 / PDF</p><p className="mt-1 font-medium">{workspace.data.statistics.papers} 篇 / {workspace.data.statistics.pdf_files} 个</p></div>
          </div>
        ) : <p className="text-sm text-red-500">无法读取工作区信息。</p>}
      </section>

      <section className="card mb-4">
        <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-2"><ShieldCheck className={`h-4 w-4 ${protection.data?.health.status === "critical" ? "text-red-500" : protection.data?.health.status === "warning" ? "text-amber-500" : "text-emerald-500"}`} /><div><h2 className="text-sm font-semibold">备份保护</h2><p className="mt-0.5 text-xs text-gray-500">最近成功备份：{formatDate(workspace.data?.last_successful_backup_at ?? null)} · 最近校验：{formatDate(workspace.data?.last_verified_at ?? null)}</p></div></div>
          <button className="btn-primary inline-flex items-center gap-2" onClick={handleCreate} disabled={createBackup.isPending || restoreBackup.isPending}>
            {createBackup.isPending ? <LoaderCircle className="h-4 w-4 animate-spin" /> : <Database className="h-4 w-4" />}立即备份
          </button>
        </div>
        {protection.data && <div className={`mb-4 rounded-lg border px-3 py-2 text-sm ${protection.data.health.status === "critical" ? "border-red-200 bg-red-50 text-red-700" : protection.data.health.status === "warning" ? "border-amber-200 bg-amber-50 text-amber-800" : "border-emerald-200 bg-emerald-50 text-emerald-800"}`}><span className="font-medium">{protection.data.health.label}</span> · {protection.data.health.reason}</div>}
        {protection.isLoading ? <p className="text-sm text-gray-500">正在读取自动备份策略…</p> : protection.data && <div className="grid gap-3 rounded-lg border border-gray-100 p-4 text-sm dark:border-slate-700 md:grid-cols-3">
          <label className="flex items-center gap-2"><input type="checkbox" checked={protection.data.policy.enabled} disabled={updateProtection.isPending} onChange={(event) => handleProtectionUpdate({ enabled: event.target.checked })} /><span>启用自动备份</span></label>
          <label className="flex flex-col gap-1 text-gray-600 dark:text-gray-300"><span className="text-xs text-gray-500">频率</span><select className="input py-1.5" value={protection.data.policy.frequency} disabled={!protection.data.policy.enabled || updateProtection.isPending} onChange={(event) => handleProtectionUpdate({ frequency: event.target.value as "daily" | "weekly" })}><option value="daily">每日</option><option value="weekly">每周</option></select></label>
          <label className="flex flex-col gap-1 text-gray-600 dark:text-gray-300"><span className="text-xs text-gray-500">保留 scheduled 份数</span><input className="input py-1.5" type="number" min="1" max="100" value={protection.data.policy.retention} disabled={!protection.data.policy.enabled || updateProtection.isPending} onChange={(event) => { const retention = Number(event.target.value); if (Number.isInteger(retention) && retention >= 1 && retention <= 100) handleProtectionUpdate({ retention }); }} /></label>
        </div>}
        <p className="mt-3 text-xs text-gray-500">自动任务只轮换 scheduled 备份；手动和紧急备份不会被自动删除。每次归档包含 PostgreSQL 逻辑 dump、PDF/附件、manifest 和 SHA-256 校验。</p>
      </section>

      <section className="card">
        <div className="mb-4 flex items-center justify-between"><h2 className="text-sm font-semibold">备份历史</h2><span className="text-xs text-gray-500">{backups.data?.length ?? 0} 个归档</span></div>
        {backups.isLoading ? <p className="text-sm text-gray-500">正在扫描备份目录…</p> : backups.data?.length ? (
          <div className="divide-y divide-gray-100 dark:divide-slate-700">
            {backups.data.map((backup) => <div key={backup.backup_id} className="flex flex-col gap-3 py-4 first:pt-0 md:flex-row md:items-center md:justify-between">
              <div className="min-w-0"><div className="flex items-center gap-2"><p className="truncate text-sm font-medium">{backup.filename}</p><span className={`rounded px-1.5 py-0.5 text-[10px] font-medium ${backup.backup_type === "emergency" ? "bg-amber-100 text-amber-700" : backup.backup_type === "scheduled" ? "bg-sky-100 text-sky-700" : "bg-slate-100 text-slate-700"}`}>{backup.backup_type === "emergency" ? "紧急" : backup.backup_type === "scheduled" ? "自动" : "手动"}</span><span className={`rounded px-1.5 py-0.5 text-[10px] font-medium ${backup.status === "invalid" ? "bg-red-100 text-red-700" : backup.status === "verified" ? "bg-emerald-100 text-emerald-700" : "bg-slate-100 text-slate-600"}`}>{backup.status === "verified" ? "已校验" : backup.status === "invalid" ? "无效" : "未校验"}</span></div><p className="mt-1 text-xs text-gray-500">{formatDate(backup.created_at)} · {formatBytes(backup.size_bytes)} · {backup.statistics.papers} 篇论文 / {backup.statistics.pdf_files} 个 PDF</p></div>
              <div className="flex items-center gap-2"><button className="btn-ghost inline-flex items-center gap-1 text-xs" onClick={() => handleVerify(backup)} disabled={verifyBackup.isPending}><CheckCircle2 className="h-3.5 w-3.5" />校验</button><button className="btn-ghost inline-flex items-center gap-1 text-xs text-amber-700" onClick={() => setRestoreTarget(backup)} disabled={restoreBackup.isPending}><RefreshCw className="h-3.5 w-3.5" />恢复</button><button className="btn-ghost p-1 text-red-500" aria-label="删除备份" onClick={() => { if (window.confirm(`删除备份 ${backup.filename}？此操作不可恢复。`)) deleteBackup.mutate(backup.backup_id); }}><Trash2 className="h-3.5 w-3.5" /></button></div>
            </div>)}
          </div>
        ) : <p className="text-sm text-gray-500">暂无备份。建议在继续创建标注和笔记前先创建一份。</p>}
      </section>

      {restoreTarget && <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/50 p-4"><div className="w-full max-w-md rounded-xl bg-white p-6 shadow-xl dark:bg-slate-900"><div className="flex items-start gap-3"><AlertTriangle className="mt-0.5 h-5 w-5 shrink-0 text-amber-500" /><div><h2 className="font-semibold">恢复此备份？</h2><p className="mt-2 text-sm text-gray-600 dark:text-gray-300">当前 Workspace 将被替换为 {formatDate(restoreTarget.created_at)} 的内容。系统会先创建紧急备份，并在恢复完成后刷新应用。</p><p className="mt-3 text-sm text-gray-500">{restoreTarget.statistics.papers} 篇论文 · {restoreTarget.statistics.documents} 个文档 · {restoreTarget.statistics.annotations} 条标注 · {restoreTarget.statistics.notes} 条笔记</p></div></div><div className="mt-6 flex justify-end gap-2"><button className="btn-ghost" onClick={() => setRestoreTarget(null)}>取消</button><button className="btn-primary bg-amber-600 hover:bg-amber-700" onClick={handleRestore} disabled={restoreBackup.isPending}>{restoreBackup.isPending ? "正在恢复…" : "验证并恢复"}</button></div></div></div>}
    </div>
  );
}
