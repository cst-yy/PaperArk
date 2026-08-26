"""Disposable historical Alembic upgrade drill for S13-B.

Run inside the backend container. Every database name is fixed, validated, and
separate from the application/test databases.
"""

from __future__ import annotations

import asyncio
import os
import subprocess

import asyncpg


ADMIN_DSN = "postgresql://paper:paper123@db:5432/postgres"
DATABASES = {
    "a6e9d2c4b7f0": "paper_workspace_s13b_s45",
    "c9d4e7f2a1b8": "paper_workspace_s13b_s8",
    "e9b4c2d7f1a6": "paper_workspace_s13b_s11",
}
USER_ID = "10000000-0000-0000-0000-000000000001"
PAPER_ID = "20000000-0000-0000-0000-000000000001"
TARGET_ID = "20000000-0000-0000-0000-000000000002"
DOCUMENT_ID = "30000000-0000-0000-0000-000000000001"
ANNOTATION_ID = "40000000-0000-0000-0000-000000000001"
NOTE_ID = "50000000-0000-0000-0000-000000000001"
TAG_ID = "60000000-0000-0000-0000-000000000001"
RELATION_ID = "70000000-0000-0000-0000-000000000001"


def database_url(name: str) -> str:
    return f"postgresql+asyncpg://paper:paper123@db:5432/{name}"


def alembic(name: str, *args: str) -> None:
    env = os.environ.copy()
    env["DATABASE_URL"] = database_url(name)
    subprocess.run(["alembic", *args], check=True, env=env)


async def recreate_database(name: str) -> None:
    if name not in DATABASES.values() or not name.startswith("paper_workspace_s13b_"):
        raise RuntimeError(f"refusing unsafe database target: {name}")
    connection = await asyncpg.connect(ADMIN_DSN)
    try:
        await connection.execute(
            "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
            "WHERE datname = $1 AND pid <> pg_backend_pid()",
            name,
        )
        await connection.execute(f'DROP DATABASE IF EXISTS "{name}"')
        await connection.execute(f'CREATE DATABASE "{name}"')
    finally:
        await connection.close()


async def seed(revision: str, name: str) -> None:
    db = await asyncpg.connect(ADMIN_DSN.rsplit("/", 1)[0] + f"/{name}")
    try:
        await db.execute(
            "INSERT INTO users(id,username,email,password_hash) VALUES($1,$2,$3,'')",
            USER_ID, f"drill-{revision}", f"{revision}@drill.local",
        )
        for paper_id, title in ((PAPER_ID, "Historical source"), (TARGET_ID, "Historical target")):
            await db.execute(
                "INSERT INTO papers(id,user_id,title,status,is_starred,notes_count) "
                "VALUES($1,$2,$3,'ready',false,0)", paper_id, USER_ID, title,
            )
        await db.execute(
            "INSERT INTO documents(id,paper_id,original_filename,file_path,file_size,mime_type,parse_status) "
            "VALUES($1,$2,'historic.pdf','pdfs/historic.pdf',17,'application/pdf','ready')",
            DOCUMENT_ID, PAPER_ID,
        )
        await db.execute(
            "INSERT INTO annotations(id,user_id,paper_id,document_id,type,page_number,selected_text,comment) "
            "VALUES($1,$2,$3,$4,'highlight',2,'historic quote','historic comment')",
            ANNOTATION_ID, USER_ID, PAPER_ID, DOCUMENT_ID,
        )
        if revision == "a6e9d2c4b7f0":
            await db.execute(
                "INSERT INTO reading_progress(id,user_id,paper_id,current_page,scroll_position,progress_percent,total_read_time) "
                "VALUES(gen_random_uuid(),$1,$2,2,0.25,50,30)", USER_ID, PAPER_ID,
            )
            await db.execute(
                "INSERT INTO notes(id,user_id,paper_id,title,content) VALUES($1,$2,$3,'Historic note','legacy markdown')",
                NOTE_ID, USER_ID, PAPER_ID,
            )
            await db.execute(
                "INSERT INTO tags(id,user_id,name,color) VALUES($1,$2,'Historic Tag','#123456')",
                TAG_ID, USER_ID,
            )
        elif revision == "c9d4e7f2a1b8":
            await db.execute(
                "INSERT INTO reading_progress(id,user_id,document_id,current_page,total_pages,progress_ratio,reading_time_seconds) "
                "VALUES(gen_random_uuid(),$1,$2,2,4,0.5,30)", USER_ID, DOCUMENT_ID,
            )
            await db.execute(
                "INSERT INTO notes(id,user_id,paper_id,title,content) VALUES($1,$2,$3,'Historic note','legacy markdown')",
                NOTE_ID, USER_ID, PAPER_ID,
            )
            await db.execute(
                "INSERT INTO tags(id,user_id,name,color,normalized_name) VALUES($1,$2,'Historic Tag','#123456','historic tag')",
                TAG_ID, USER_ID,
            )
        else:
            await db.execute(
                "INSERT INTO reading_progress(id,user_id,document_id,current_page,total_pages,progress_ratio,reading_time_seconds) "
                "VALUES(gen_random_uuid(),$1,$2,2,4,0.5,30)", USER_ID, DOCUMENT_ID,
            )
            await db.execute(
                "INSERT INTO notes(id,user_id,paper_id,title,content_markdown,note_type,embedding_status) "
                "VALUES($1,$2,$3,'Historic research','structured markdown','research','pending')",
                NOTE_ID, USER_ID, PAPER_ID,
            )
            evidence_id = "51000000-0000-0000-0000-000000000001"
            profile_id = "52000000-0000-0000-0000-000000000001"
            analysis_id = "53000000-0000-0000-0000-000000000001"
            await db.execute(
                "INSERT INTO note_evidence(id,note_id,annotation_id,order_index,quote_snapshot) VALUES($1,$2,$3,0,'historic quote')",
                evidence_id, NOTE_ID, ANNOTATION_ID,
            )
            await db.execute(
                "INSERT INTO research_note_profiles(id,note_id,research_problem,future_work) VALUES($1,$2,'historic problem','historic future')",
                profile_id, NOTE_ID,
            )
            await db.execute(
                "INSERT INTO ai_analyses(id,user_id,paper_id,provider_name,model,prompt_version,retrieval_mode,source_snapshot_hash,input_hash,result_json) "
                "VALUES($1,$2,$3,'drill','model','v1','hybrid',repeat('a',64),repeat('b',64),'{}')",
                analysis_id, USER_ID, PAPER_ID,
            )
            await db.execute(
                "INSERT INTO ai_analysis_sources(id,analysis_id,order_index,source_key,source_type,paper_id,document_id,title,content_snapshot,content_hash) "
                "VALUES(gen_random_uuid(),$1,0,'S1','chunk',$2,$3,'Historic source','source snapshot',repeat('c',64))",
                analysis_id, PAPER_ID, DOCUMENT_ID,
            )
            await db.execute(
                "INSERT INTO tags(id,user_id,name,color,normalized_name) VALUES($1,$2,'Historic Tag','#123456','historic tag')",
                TAG_ID, USER_ID,
            )
        await db.execute(
            "INSERT INTO paper_tags(id,paper_id,tag_id) VALUES(gen_random_uuid(),$1,$2)", PAPER_ID, TAG_ID,
        )
        await db.execute(
            "INSERT INTO paper_relations(id,source_paper_id,target_paper_id,relation_type,score) VALUES($1,$2,$3,'cites',0.9)",
            RELATION_ID, PAPER_ID, TARGET_ID,
        )
        await db.execute(
            "INSERT INTO settings(id,user_id,key,value) VALUES(gen_random_uuid(),$1,'drill.setting','preserved')",
            USER_ID,
        )
    finally:
        await db.close()


async def verify(name: str, revision: str) -> dict[str, object]:
    db = await asyncpg.connect(ADMIN_DSN.rsplit("/", 1)[0] + f"/{name}")
    try:
        values = {
            "revision": await db.fetchval("SELECT version_num FROM alembic_version"),
            "papers": await db.fetchval("SELECT count(*) FROM papers"),
            "documents": await db.fetchval("SELECT count(*) FROM documents WHERE original_filename='historic.pdf'"),
            "annotations": await db.fetchval("SELECT count(*) FROM annotations WHERE selected_text='historic quote' AND document_id=$1", DOCUMENT_ID),
            "reading_progress": await db.fetchval("SELECT count(*) FROM reading_progress WHERE document_id=$1 AND current_page=2", DOCUMENT_ID),
            "notes": await db.fetchval("SELECT count(*) FROM notes WHERE content_markdown LIKE '%markdown%'"),
            "tags": await db.fetchval("SELECT count(*) FROM tags WHERE normalized_name='historic tag'"),
            "relations": await db.fetchval("SELECT count(*) FROM paper_relations WHERE id=$1 AND user_id=$2 AND origin='reference'", RELATION_ID, USER_ID),
            "settings": await db.fetchval("SELECT count(*) FROM settings WHERE key='drill.setting' AND value='preserved'"),
        }
        if revision == "e9b4c2d7f1a6":
            values.update({
                "note_evidence": await db.fetchval("SELECT count(*) FROM note_evidence WHERE quote_snapshot='historic quote'"),
                "research_profiles": await db.fetchval("SELECT count(*) FROM research_note_profiles WHERE research_problem='historic problem'"),
                "ai_analyses": await db.fetchval("SELECT count(*) FROM ai_analyses WHERE provider_name='drill'"),
                "ai_sources": await db.fetchval("SELECT count(*) FROM ai_analysis_sources WHERE content_snapshot='source snapshot'"),
            })
        expected = {key: 1 for key in values if key not in {"revision", "papers"}}
        expected["papers"] = 2
        if values["revision"] != "c4e8a1d7b3f9" or any(values[key] != value for key, value in expected.items()):
            raise AssertionError({"stage": revision, "values": values, "expected": expected})
        return values
    finally:
        await db.close()


async def main() -> None:
    results = {}
    for revision, name in DATABASES.items():
        await recreate_database(name)
        alembic(name, "upgrade", revision)
        await seed(revision, name)
        alembic(name, "upgrade", "head")
        results[revision] = await verify(name, revision)
    for revision, result in results.items():
        print(revision, result)


if __name__ == "__main__":
    asyncio.run(main())
