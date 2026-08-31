import uuid
from io import BytesIO
from zipfile import ZIP_DEFLATED, ZipFile
from xml.sax.saxutils import escape
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Response

from app.core.database import get_current_user_id
from app.schemas.paper_list import (
    BatchPaperDelete, BatchPaperUpdate, PaperListPage, PaperListPreference,
    PaperListExportRequest, PaperListSort, SortOrder, PaperListViewSettings, PaperListViewSettingsPatch,
)
from app.services.paper_list_service import PaperListService, get_paper_list_service
from app.services.paper_service import PaperService, get_paper_service
from app.core.exceptions import InvalidFolderError, InvalidTagError, PaperNotFoundError
from app.core.exceptions import RevisionConflictError

router = APIRouter()

EXPORT_LABELS = {
    "title": "标题", "title_zh": "中文标题", "abstract": "摘要", "authors": "作者", "journal": "期刊",
    "conference": "会议", "publication_year": "年份", "keywords": "关键词", "tags": "标签", "folders": "文件夹",
    "doi": "DOI", "arxiv_id": "arXiv ID", "url": "URL", "publisher": "出版社", "citation_text": "引用文本",
    "citation_count": "引用数", "reading_status": "阅读状态", "starred": "收藏", "notes": "笔记数",
    "created_at": "创建时间", "updated_at": "更新时间",
}


def _excel_column(index: int) -> str:
    value = ""
    while index:
        index, remainder = divmod(index - 1, 26)
        value = chr(65 + remainder) + value
    return value


def _build_xlsx(headers: list[str], rows: list[list[object]]) -> bytes:
    """Create a small, standards-compliant XLSX using only the stdlib."""
    xml_rows = []
    for row_index, row in enumerate([headers, *rows], start=1):
        cells = []
        for column_index, value in enumerate(row, start=1):
            reference = f"{_excel_column(column_index)}{row_index}"
            if value is None:
                cells.append(f'<c r="{reference}"/>')
            elif isinstance(value, (int, float)) and not isinstance(value, bool):
                cells.append(f'<c r="{reference}"><v>{value}</v></c>')
            else:
                text = escape(str(value))
                cells.append(f'<c r="{reference}" t="inlineStr"><is><t xml:space="preserve">{text}</t></is></c>')
        xml_rows.append(f'<row r="{row_index}">{"".join(cells)}</row>')
    worksheet = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>' \
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData>' \
        + "".join(xml_rows) + '</sheetData></worksheet>'
    output = BytesIO()
    with ZipFile(output, "w", ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", '<?xml version="1.0" encoding="UTF-8"?>' \
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">' \
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>' \
            '<Default Extension="xml" ContentType="application/xml"/>' \
            '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>' \
            '<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>' \
            '</Types>')
        archive.writestr("_rels/.rels", '<?xml version="1.0" encoding="UTF-8"?>' \
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">' \
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>' \
            '</Relationships>')
        archive.writestr("xl/workbook.xml", '<?xml version="1.0" encoding="UTF-8"?>' \
            '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">' \
            '<sheets><sheet name="论文列表" sheetId="1" r:id="rId1"/></sheets></workbook>')
        archive.writestr("xl/_rels/workbook.xml.rels", '<?xml version="1.0" encoding="UTF-8"?>' \
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">' \
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>' \
            '</Relationships>')
        archive.writestr("xl/worksheets/sheet1.xml", worksheet)
    return output.getvalue()


@router.get("/", response_model=PaperListPage)
async def list_papers(
    q: str | None = None, year_from: int | None = Query(None, ge=1000, le=9999), year_to: int | None = Query(None, ge=1000, le=9999),
    journal: str | None = None, author: str | None = None, tag_id: uuid.UUID | None = None, keyword: str | None = None,
    reading_status: Literal["unread", "reading", "finished", "archived"] | None = None, starred: bool | None = None,
    sort: PaperListSort = "updated_at", order: SortOrder = "desc", page: int = Query(1, ge=1),
    page_size: Literal["25", "50", "100", "200"] = "50",
    service: PaperListService = Depends(get_paper_list_service), user_id: uuid.UUID = Depends(get_current_user_id),
):
    return await service.list_rows(user_id, q=q, year_from=year_from, year_to=year_to, journal=journal, author=author,
        tag_id=tag_id, keyword=keyword, reading_status=reading_status, starred=starred, sort=sort, order=order,
        page=page, page_size=int(page_size))


@router.get("/preference", response_model=PaperListPreference)
async def get_preference(
    service: PaperListService = Depends(get_paper_list_service),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    return await service.get_preference(user_id)


@router.put("/preference", response_model=PaperListPreference)
async def save_preference(
    preference: PaperListPreference,
    service: PaperListService = Depends(get_paper_list_service),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    return await service.save_preference(user_id, preference)


@router.get("/view-settings", response_model=PaperListViewSettings)
async def get_view_settings(
    service: PaperListService = Depends(get_paper_list_service),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    return await service.get_view_settings(user_id)


@router.patch("/view-settings", response_model=PaperListViewSettings)
async def patch_view_settings(
    patch: PaperListViewSettingsPatch,
    service: PaperListService = Depends(get_paper_list_service),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    try:
        return await service.patch_view_settings(user_id, patch)
    except RevisionConflictError as error:
        raise HTTPException(status_code=409, detail=error.message) from error


@router.post("/batch-update")
async def batch_update(
    data: BatchPaperUpdate,
    service: PaperListService = Depends(get_paper_list_service),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    try:
        count = await service.batch_update(user_id, data)
    except PaperNotFoundError as error:
        raise HTTPException(status_code=404, detail=error.message) from error
    except (InvalidTagError, InvalidFolderError) as error:
        raise HTTPException(status_code=400, detail=error.message) from error
    return {"updated": count}


@router.post("/batch-delete")
async def batch_delete(
    data: BatchPaperDelete,
    service: PaperService = Depends(get_paper_service),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    try:
        count = await service.delete_papers_atomic(user_id, data.paper_ids)
    except PaperNotFoundError as error:
        raise HTTPException(status_code=404, detail=error.message) from error
    return {"deleted": count}


@router.post("/export.xlsx")
async def export_papers(
    data: PaperListExportRequest,
    service: PaperListService = Depends(get_paper_list_service),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    columns = data.columns or list(EXPORT_LABELS)
    page = await service.list_rows(
        user_id, q=None, year_from=None, year_to=None, journal=None, author=None, tag_id=None, keyword=None,
        reading_status=None, starred=None, sort="updated_at", order="desc", page=1, page_size=100000,
        paper_ids=data.paper_ids,
    )
    export_rows = []
    for row in page.items:
        values = row.model_dump()
        values["authors"] = "; ".join(item.name for item in row.authors)
        for field in ("keywords", "tags", "folders"):
            values[field] = "; ".join(item.name for item in getattr(row, field))
        values["notes"] = row.note_count
        values["starred"] = "是" if row.starred else "否"
        values["created_at"] = row.created_at.isoformat()
        values["updated_at"] = row.updated_at.isoformat()
        export_rows.append([values.get(column) for column in columns])
    return Response(
        _build_xlsx([EXPORT_LABELS[column] for column in columns], export_rows),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="paperark-papers.xlsx"'},
    )
