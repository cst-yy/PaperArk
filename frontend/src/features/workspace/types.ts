export interface BackupStatistics {
  papers: number;
  documents: number;
  annotations: number;
  notes: number;
  pdf_files: number;
}

export interface BackupPolicy {
  enabled: boolean;
  frequency: "daily" | "weekly";
  retention: number;
  last_scheduled_backup_at: string | null;
  last_backup_status: "success" | "failed" | "never";
  last_backup_error: string | null;
  last_verified_at: string | null;
  last_verified_backup_id: string | null;
  last_verification_status: "valid" | "invalid" | "never";
}

export interface BackupHealth {
  status: "healthy" | "warning" | "critical";
  label: string;
  reason: string;
  last_successful_backup_at: string | null;
  last_verified_at: string | null;
  backup_due: boolean;
  policy: BackupPolicy;
}

export interface WorkspaceSettingsResponse {
  policy: BackupPolicy;
  health: BackupHealth;
}

export interface WorkspaceInfo {
  workspace_id: string;
  name: string;
  workspace_path: string;
  backup_path: string;
  database_bytes: number;
  storage_bytes: number;
  storage_file_count: number;
  statistics: BackupStatistics;
  last_backup_at: string | null;
  last_successful_backup_at: string | null;
  last_verified_at: string | null;
  backup_health: BackupHealth | null;
}

export interface BackupItem {
  backup_id: string;
  filename: string;
  created_at: string;
  size_bytes: number;
  format_version: number;
  schema_revision: string;
  backup_type: "manual" | "scheduled" | "emergency" | string;
  status: "unknown" | "verified" | "invalid" | "unsupported";
  statistics: BackupStatistics;
}

export interface BackupVerificationResult {
  valid: boolean;
  status: "valid" | "invalid" | "unsupported" | "corrupted";
  errors: string[];
  warnings: string[];
}

export interface RestoreResult {
  restored_backup_id: string;
  emergency_backup_id: string;
  statistics: BackupStatistics;
}
