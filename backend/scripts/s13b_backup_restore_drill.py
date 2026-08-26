"""Real backup/restart/restore and failure drill on an isolated workspace."""

from __future__ import annotations

import asyncio
import hashlib
import json
import shutil
import subprocess
import uuid
import zipfile
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import engine
from app.services.backup_service import BackupError, BackupService


TABLES = (
    "papers", "documents", "annotations", "reading_progress", "notes",
    "note_evidence", "research_note_profiles", "ai_analyses",
    "ai_analysis_sources", "references", "paper_relations", "graph_layouts",
    "settings",
)
WORKSPACE_ID = uuid.UUID("91000000-0000-0000-0000-000000000001")
USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
PAPER_ID = uuid.UUID("92000000-0000-0000-0000-000000000001")
TARGET_ID = uuid.UUID("92000000-0000-0000-0000-000000000002")
DOCUMENT_ID = uuid.UUID("93000000-0000-0000-0000-000000000001")
ANNOTATION_ID = uuid.UUID("94000000-0000-0000-0000-000000000001")
NOTE_ID = uuid.UUID("95000000-0000-0000-0000-000000000001")
REFERENCE_ID = uuid.UUID("96000000-0000-0000-0000-000000000001")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


async def integrity(db: AsyncSession) -> dict[str, object]:
    counts = {}
    for table in TABLES:
        table_name = f'"{table}"' if table == "references" else table
        predicate = " WHERE key = 'integrity.setting'" if table == "settings" else ""
        counts[table] = int((await db.execute(text(
            f"SELECT count(*) FROM {table_name}{predicate}"
        ))).scalar_one())
    documents = (await db.execute(text("SELECT file_path, file_hash FROM documents ORDER BY file_path"))).all()
    file_hashes = {
        path: sha256(settings.storage_path / path)
        for path, _ in documents
        if (settings.storage_path / path).is_file()
    }
    return {
        "workspace_id": json.loads((settings.workspace_path / "workspace.json").read_text())["workspace_id"],
        "schema_revision": str((await db.execute(text("SELECT version_num FROM alembic_version"))).scalar_one()),
        "counts": counts,
        "pdf_sha256": file_hashes,
        "document_file_hash": {path: value for path, value in documents},
    }


async def seed(db: AsyncSession) -> None:
    pdf = settings.storage_path / "pdfs" / "integrity.pdf"
    pdf.write_bytes(b"%PDF-1.4\nS13-B integrity fixture\n%%EOF\n")
    digest = sha256(pdf)
    statements = [
        ("INSERT INTO users(id,username,email,password_hash) VALUES(:u,'researcher','researcher@local','')", {"u": USER_ID}),
        ("INSERT INTO papers(id,user_id,title,status,reading_status,is_starred,notes_count) VALUES(:p,:u,'Integrity source','ready','reading',false,1),(:t,:u,'Integrity target','ready','unread',false,0)", {"p": PAPER_ID, "t": TARGET_ID, "u": USER_ID}),
        ("INSERT INTO documents(id,paper_id,original_filename,file_path,file_size,mime_type,file_hash,parse_status,page_count) VALUES(:d,:p,'integrity.pdf','pdfs/integrity.pdf',39,'application/pdf',:h,'ready',1)", {"d": DOCUMENT_ID, "p": PAPER_ID, "h": digest}),
        ("INSERT INTO annotations(id,user_id,paper_id,document_id,type,page_number,selected_text,comment,position_data) VALUES(:a,:u,:p,:d,'highlight',1,'integrity quote','evidence','{}')", {"a": ANNOTATION_ID, "u": USER_ID, "p": PAPER_ID, "d": DOCUMENT_ID}),
        ("INSERT INTO reading_progress(id,user_id,document_id,current_page,total_pages,progress_ratio,reading_time_seconds) VALUES(gen_random_uuid(),:u,:d,1,1,1,12)", {"u": USER_ID, "d": DOCUMENT_ID}),
        ("INSERT INTO notes(id,user_id,paper_id,title,content_markdown,note_type,embedding_status) VALUES(:n,:u,:p,'Integrity note','grounded note','research','pending')", {"n": NOTE_ID, "u": USER_ID, "p": PAPER_ID}),
        ("INSERT INTO note_evidence(id,note_id,annotation_id,order_index,quote_snapshot) VALUES(gen_random_uuid(),:n,:a,0,'integrity quote')", {"n": NOTE_ID, "a": ANNOTATION_ID}),
        ("INSERT INTO research_note_profiles(id,note_id,research_problem,future_work,revision) VALUES(gen_random_uuid(),:n,'integrity problem','integrity future',2)", {"n": NOTE_ID}),
        ("INSERT INTO ai_analyses(id,user_id,paper_id,provider_name,model,prompt_version,retrieval_mode,source_snapshot_hash,input_hash,result_json) VALUES(gen_random_uuid(),:u,:p,'drill','model','v1','hybrid',repeat('a',64),repeat('b',64),'{}')", {"u": USER_ID, "p": PAPER_ID}),
        ("INSERT INTO ai_analysis_sources(id,analysis_id,order_index,source_key,source_type,paper_id,document_id,title,content_snapshot,content_hash) SELECT gen_random_uuid(),id,0,'S1','chunk',:p,:d,'source','snapshot',repeat('c',64) FROM ai_analyses", {"p": PAPER_ID, "d": DOCUMENT_ID}),
        ("INSERT INTO \"references\"(id,document_id,order_index,raw_text,page_start,page_end,title,matched_paper_id,match_method,match_confidence) VALUES(:r,:d,0,'historic citation',1,1,'Integrity target',:t,'title_exact',1)", {"r": REFERENCE_ID, "d": DOCUMENT_ID, "t": TARGET_ID}),
        ("INSERT INTO paper_relations(id,user_id,source_paper_id,target_paper_id,relation_type,origin,source_reference_id,confidence) VALUES(gen_random_uuid(),:u,:p,:t,'cites','reference',:r,1)", {"u": USER_ID, "p": PAPER_ID, "t": TARGET_ID, "r": REFERENCE_ID}),
        ("INSERT INTO graph_layouts(id,user_id,graph_type,scope_key,layout_json) VALUES(gen_random_uuid(),:u,'citation','workspace:depth:1','{\"nodes\":{}}')", {"u": USER_ID}),
        ("INSERT INTO settings(id,user_id,key,value) VALUES(gen_random_uuid(),:u,'integrity.setting','preserved')", {"u": USER_ID}),
    ]
    for statement, params in statements:
        await db.execute(text(statement), params)
    await db.commit()


def malformed_copy(source: Path, target: Path, *, corrupt_pdf: bool = False) -> None:
    with zipfile.ZipFile(source, "r") as original, zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as output:
        for item in original.infolist():
            payload = original.read(item.filename)
            if item.filename == "manifest.json" and not corrupt_pdf:
                data = json.loads(payload)
                data["format_version"] = 999
                payload = json.dumps(data).encode()
            elif corrupt_pdf and item.filename.startswith("storage/"):
                payload += b"corrupted"
            output.writestr(item, payload)


class StagingFailureService(BackupService):
    async def _restore_database(self, dump_path: Path) -> None:
        if not getattr(self, "_failed_once", False):
            self._failed_once = True
            raise BackupError("injected restore staging failure")
        await super()._restore_database(dump_path)


async def main() -> None:
    if "s13b_restore" not in settings.DATABASE_URL or "s13b-workspace" not in str(settings.workspace_path):
        raise RuntimeError("refusing to run outside the isolated S13-B database/workspace")
    shutil.rmtree(settings.workspace_path, ignore_errors=True)
    settings.workspace_path.mkdir(parents=True, exist_ok=True)
    settings.storage_path
    settings.backup_path
    (settings.workspace_path / "workspace.json").write_text(json.dumps({
        "format": "AIResearchWorkspace", "workspace_id": str(WORKSPACE_ID),
        "name": "S13-B Drill", "database": {"major_version": 16},
    }))

    async with AsyncSession(engine, expire_on_commit=False) as db:
        await seed(db)
        service = BackupService(db)
        before = await integrity(db)
        backup = await service.create_backup()
        verified = await service.verify_backup(backup.backup_id)
        assert verified.valid
        backup_file = service._find_backup(backup.backup_id)

    subprocess.run(["alembic", "upgrade", "head"], check=True)
    await engine.dispose()
    async with AsyncSession(engine, expire_on_commit=False) as restarted:
        after_upgrade_restart = await integrity(restarted)
    assert before == after_upgrade_restart

    async with AsyncSession(engine, expire_on_commit=False) as changed:
        await changed.execute(text("DELETE FROM graph_layouts"))
        await changed.execute(text("DELETE FROM ai_analyses"))
        await changed.execute(text("DELETE FROM paper_relations"))
        await changed.commit()
    (settings.storage_path / "pdfs" / "integrity.pdf").write_bytes(b"changed")

    async with AsyncSession(engine, expire_on_commit=False) as restore_db:
        restored = await BackupService(restore_db).restore_backup(backup.backup_id)
        assert restored.restored_backup_id == backup.backup_id
    await engine.dispose()
    async with AsyncSession(engine, expire_on_commit=False) as restored_db:
        after_restore = await integrity(restored_db)
    assert before == after_restore

    # Keep adversarial copies outside BACKUP_DIR so lookup by backup_id cannot
    # confuse them with the verified restore source.
    corrupt = settings.workspace_path / "corrupted.airw"
    malformed = settings.workspace_path / "malformed.airw"
    malformed_copy(backup_file, corrupt, corrupt_pdf=True)
    malformed_copy(backup_file, malformed)
    async with AsyncSession(engine, expire_on_commit=False) as verify_db:
        verifier = BackupService(verify_db)
        corrupt_result = await verifier._verify_path(corrupt)
        malformed_result = await verifier._verify_path(malformed)
        assert not corrupt_result.valid and corrupt_result.status == "corrupted"
        assert not malformed_result.valid and malformed_result.status == "unsupported"
        stable = await integrity(verify_db)
        try:
            await StagingFailureService(verify_db).restore_backup(backup.backup_id)
        except BackupError as error:
            assert "已自动回退" in str(error)
        else:
            raise AssertionError("injected restore failure was not rejected")
    await engine.dispose()
    async with AsyncSession(engine, expire_on_commit=False) as final_db:
        after_failure = await integrity(final_db)
    assert stable == after_failure == before

    print(json.dumps({
        "before": before,
        "after_upgrade_restart": after_upgrade_restart,
        "after_restore": after_restore,
        "after_injected_failure": after_failure,
        "backup": backup.filename,
        "emergency_backup": str(restored.emergency_backup_id),
        "corrupted_status": corrupt_result.status,
        "malformed_status": malformed_result.status,
    }, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
