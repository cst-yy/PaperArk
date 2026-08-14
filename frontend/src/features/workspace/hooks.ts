import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { createBackup, deleteBackup, getBackupProtection, getWorkspaceInfo, listBackups, restoreBackup, updateBackupProtection, verifyBackup } from "./api";

const workspaceKey = ["workspace"] as const;
const backupsKey = ["workspace", "backups"] as const;

export function useWorkspaceInfo() {
  return useQuery({ queryKey: workspaceKey, queryFn: getWorkspaceInfo, refetchInterval: 30_000 });
}

export function useBackups() {
  return useQuery({ queryKey: backupsKey, queryFn: listBackups, refetchInterval: 30_000 });
}

export function useBackupProtection() {
  return useQuery({ queryKey: ["workspace", "protection"], queryFn: getBackupProtection, refetchInterval: 30_000 });
}

export function useUpdateBackupProtection() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: updateBackupProtection,
    onSuccess: (data) => {
      queryClient.setQueryData(["workspace", "protection"], data);
      queryClient.invalidateQueries({ queryKey: workspaceKey });
    },
  });
}

export function useCreateBackup() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: createBackup,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: workspaceKey });
      queryClient.invalidateQueries({ queryKey: backupsKey });
    },
  });
}

export function useVerifyBackup() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: verifyBackup,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: workspaceKey });
      queryClient.invalidateQueries({ queryKey: ["workspace", "protection"] });
      queryClient.invalidateQueries({ queryKey: backupsKey });
    },
  });
}

export function useDeleteBackup() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: deleteBackup,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: backupsKey }),
  });
}

export function useRestoreBackup() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: restoreBackup,
    onSuccess: () => {
      queryClient.clear();
    },
  });
}
