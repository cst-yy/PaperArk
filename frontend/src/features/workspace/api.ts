import { api } from "@/services/api";
import type { BackupItem, BackupVerificationResult, RestoreResult, WorkspaceInfo, WorkspaceSettingsResponse, BackupPolicy } from "./types";

export async function getWorkspaceInfo(): Promise<WorkspaceInfo> {
  return (await api.get<WorkspaceInfo>("/workspace/")).data;
}

export async function getBackupProtection(): Promise<WorkspaceSettingsResponse> {
  return (await api.get<WorkspaceSettingsResponse>("/workspace/protection")).data;
}

export async function updateBackupProtection(update: Partial<Pick<BackupPolicy, "enabled" | "frequency" | "retention">>): Promise<WorkspaceSettingsResponse> {
  return (await api.put<WorkspaceSettingsResponse>("/workspace/protection", update)).data;
}

export async function listBackups(): Promise<BackupItem[]> {
  return (await api.get<BackupItem[]>("/workspace/backups")).data;
}

export async function createBackup(): Promise<BackupItem> {
  return (await api.post<BackupItem>("/workspace/backups")).data;
}

export async function verifyBackup(backupId: string): Promise<BackupVerificationResult> {
  return (await api.post<BackupVerificationResult>(`/workspace/backups/${backupId}/verify`)).data;
}

export async function restoreBackup(backupId: string): Promise<RestoreResult> {
  return (await api.post<RestoreResult>(`/workspace/backups/${backupId}/restore`)).data;
}

export async function deleteBackup(backupId: string): Promise<void> {
  await api.delete(`/workspace/backups/${backupId}`);
}
