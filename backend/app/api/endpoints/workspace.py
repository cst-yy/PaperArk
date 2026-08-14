import uuid

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.database import get_current_user_id
from app.schemas.backup import (
    BackupItem,
    BackupVerificationResult,
    RestoreResult,
    WorkspaceInfo,
)
from app.schemas.workspace import BackupPolicy, BackupPolicyUpdate, WorkspaceSettingsResponse
from app.services.workspace_settings_service import WorkspaceSettingsService
from app.services.backup_service import (
    BackupError,
    BackupNotFoundError,
    BackupService,
    get_backup_service,
)

router = APIRouter()


def _handle_backup_error(error: BackupError) -> None:
    if isinstance(error, BackupNotFoundError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error


@router.get("/", response_model=WorkspaceInfo)
async def get_workspace(service: BackupService = Depends(get_backup_service)):
    try:
        return await service.get_workspace_info()
    except BackupError as error:
        _handle_backup_error(error)


@router.get("/protection", response_model=WorkspaceSettingsResponse)
async def get_backup_protection(
    service: BackupService = Depends(get_backup_service),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    policy_service = WorkspaceSettingsService(service.db)
    policy = await policy_service.get_backup_policy(user_id)
    workspace = await service.get_workspace_info()
    return WorkspaceSettingsResponse(policy=policy, health=workspace.backup_health)


@router.put("/protection", response_model=WorkspaceSettingsResponse)
async def update_backup_protection(
    update: BackupPolicyUpdate,
    service: BackupService = Depends(get_backup_service),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    policy = await WorkspaceSettingsService(service.db).update_backup_policy(user_id, update)
    workspace = await service.get_workspace_info()
    return WorkspaceSettingsResponse(policy=policy, health=workspace.backup_health)


@router.get("/backups", response_model=list[BackupItem])
async def list_backups(service: BackupService = Depends(get_backup_service)):
    return await service.list_backups()


@router.post("/backups", response_model=BackupItem, status_code=status.HTTP_201_CREATED)
async def create_backup(service: BackupService = Depends(get_backup_service)):
    try:
        return await service.create_backup()
    except BackupError as error:
        _handle_backup_error(error)


@router.get("/backups/{backup_id}", response_model=BackupItem)
async def get_backup(backup_id: uuid.UUID, service: BackupService = Depends(get_backup_service)):
    try:
        return await service.get_backup(backup_id)
    except BackupError as error:
        _handle_backup_error(error)


@router.post("/backups/{backup_id}/verify", response_model=BackupVerificationResult)
async def verify_backup(backup_id: uuid.UUID, service: BackupService = Depends(get_backup_service)):
    try:
        return await service.verify_backup(backup_id)
    except BackupError as error:
        _handle_backup_error(error)


@router.post("/backups/{backup_id}/restore", response_model=RestoreResult)
async def restore_backup(backup_id: uuid.UUID, service: BackupService = Depends(get_backup_service)):
    try:
        return await service.restore_backup(backup_id)
    except BackupError as error:
        _handle_backup_error(error)


@router.delete("/backups/{backup_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_backup(backup_id: uuid.UUID, service: BackupService = Depends(get_backup_service)):
    try:
        await service.delete_backup(backup_id)
    except BackupError as error:
        _handle_backup_error(error)
