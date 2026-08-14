from datetime import UTC, datetime, timedelta

from app.schemas.workspace import BackupPolicy
from app.services.workspace_settings_service import WorkspaceSettingsService


def test_daily_policy_becomes_due_after_one_day():
    now = datetime(2026, 8, 13, tzinfo=UTC)
    policy = BackupPolicy(enabled=True, last_scheduled_backup_at=now - timedelta(days=1))

    assert WorkspaceSettingsService.is_due(policy, now)


def test_disabled_policy_is_never_due():
    policy = BackupPolicy(enabled=False)

    assert not WorkspaceSettingsService.is_due(policy)


def test_health_requires_recent_verified_backup():
    now = datetime(2026, 8, 13, tzinfo=UTC)
    healthy_policy = BackupPolicy(
        last_scheduled_backup_at=now - timedelta(hours=1),
        last_verified_at=now - timedelta(minutes=30),
        last_verification_status="valid",
    )
    warning_policy = BackupPolicy(
        last_scheduled_backup_at=now - timedelta(hours=1),
        last_verification_status="never",
    )

    healthy = WorkspaceSettingsService.build_health(healthy_policy, now - timedelta(hours=1), True, now)
    warning = WorkspaceSettingsService.build_health(warning_policy, now - timedelta(hours=1), True, now)
    critical = WorkspaceSettingsService.build_health(healthy_policy, now - timedelta(hours=1), False, now)

    assert healthy.status == "healthy"
    assert warning.status == "warning"
    assert critical.status == "critical"
