# AI Research Workspace

个人科研论文工作台 — 论文管理 + PDF 阅读 + 标注 + 笔记 + AI 辅助

定位：Zotero + Obsidian + AI Research Assistant 的结合体。

---

## 技术栈

| 层 | 技术 |
|---|---|
| 前端 | React 18 + TypeScript + Vite + Tailwind CSS + Zustand + React Query |
| 后端 | Python 3.12 + FastAPI + SQLAlchemy 2.0 (async) + Pydantic v2 |
| 数据库 | PostgreSQL 16 + pgvector |
| 缓存/队列 | Redis 7 |

---

## 快速开始

### 方式一：Docker（推荐）

```bash
docker-compose up -d
```

启动后访问：

| 服务 | 地址 |
|---|---|
| 前端 | http://localhost:5173 |
| 后端 API | http://localhost:8000 |
| Swagger 文档 | http://localhost:8000/docs |
| ReDoc 文档 | http://localhost:8000/redoc |

### 方式二：手动启动

**1. 启动 PostgreSQL + Redis（只启动基础设施）**

```bash
docker-compose up -d db redis
```

**2. 启动后端**

```bash
cd backend
python -m venv venv
# Windows: venv\Scripts\activate
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# 先通过 Alembic 升级 schema，再启动并种子默认用户
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

**3. 种子示例数据（可选，幂等可重复执行）**

```bash
cd backend
python -m app.seed
```

种子数据包含 5 篇联邦学习相关论文、3 个文件夹、8 个标签。

**4. 启动前端**

```bash
cd frontend
npm install
npm run dev
```

> 前端 Vite 开发代理已配置 `/api` -> `http://backend:8000`（Docker）或 `http://localhost:8000`（手动）。

---

## 架构设计

### 三层分层

```
API Layer (endpoints/)
    │  解析 HTTP 请求 → 调 Service → 返回 Pydantic 响应
    │  捕获业务异常 → 转换为 HTTP 状态码
    ▼
Service Layer (services/)
    │  业务编排：作者去重、Tag/Folder 校验、重复检测、删除一致性
    │  PDF 导入：校验 → 存储 → 创建 Paper+Document → 异常补偿
    │  抛出 Domain Exception，不关心 HTTP
    ▼
Repository Layer (repositories/)
    │  数据访问：所有查询带 user_id 隔离、分页、筛选
    │  纯 SQL 操作，不处理业务规则
    ▼
Model (models/)
    ORM 实体定义
```

### 核心设计原则

1. **API 不写 SQL** — 只解析请求、调 Service、返回响应
2. **Service 不关心 HTTP** — 抛业务异常（`PaperNotFoundError` 等），API 层转换
3. **Repository 不处理业务规则** — 只管数据读写，带 `user_id` 隔离
4. **Model 不承担接口序列化** — 序列化由 `PaperMapper` 负责
5. **Storage 层统一文件操作** — PDF 校验、UUID 存储、路径解析、文件删除

### 用户隔离

P0 单用户模式，所有查询统一带 `Paper.user_id == user_id`。

```python
# database.py
DEFAULT_USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")

def get_current_user_id() -> uuid.UUID:
    """FastAPI dependency — 替换为 JWT 解析即可升级多用户"""
    return DEFAULT_USER_ID
```

Document 查询通过 JOIN Paper 实现 user_id 隔离：

```python
# DocumentRepository.get_by_id()
select(Document)
    .join(Paper, Document.paper_id == Paper.id)
    .where(Document.id == document_id, Paper.user_id == user_id)
```

### 作者去重策略

```
ORCID 精确匹配
    ↓ 未命中
name + affiliation 模糊匹配（同名不同机构不合并）
    ↓ 未命中
创建新 Author
```

`find_authors_by_names()` 返回 `dict[str, list[Author]]`，支持同名多作者按 affiliation 精确匹配。

### ORCID 规范化

输入可能是 `https://orcid.org/0000-0002-1825-0097`、`ORCID: 0000-0002-1825-0097`、`0000000218250097`（无连字符）等，
统一提取为 `0000-0002-1825-0097` 格式存储。非法 ORCID 返回 `None`。

### 删除一致性

```python
# Service 层：先 commit，后删文件
await self.repo.delete(paper)
await self.db.commit()         # ← 显式提交
# commit 成功后才删物理文件
if pdf_path:
    full_path.unlink()
```

如果 commit 失败，文件不动。如果文件删除失败，DB 记录已删，孤儿文件只记日志。

### 重复检测

- **Create**：DOI → arXiv ID → title + year，命中则拒绝
- **Update**：修改 doi/arxiv_id/title/publication_year 时重新检测，排除自身

### Tag/Folder 校验

- Pydantic 层自动去重（`field_validator` 去重 `tag_ids`/`folder_ids`）
- Service 层二次去重（`dict.fromkeys` 保序去重）
- 校验返回的 valid 数量与去重后的请求对比

---

## Paper / Document 职责边界

```
Paper          — 论文知识实体（标题、摘要、DOI、作者、标签...）
   │
   │ 1 : 1（P0）/ 1 : N（未来）
   ↓
Document       — PDF 文件实体（file_path, original_filename, file_size, parse_status）
   │
   ↓
storage/pdfs/{uuid}.pdf
```

- `Document.file_path` 是权威文件路径
- `Paper.pdf_path` 已废弃，保留仅为向后兼容
- 删除 Paper 时优先从 Document 读取文件路径
- Migration 路线：S3 保留兼容 → S4+ 新代码只读 `Document.file_path` → 后续删除 `Paper.pdf_path`

### PDF 文件存储

- 所有文件以 UUID 命名（`pdfs/{uuid}.pdf`），不使用原始文件名
- 原始文件名保存在 `Document.original_filename` 作为 metadata
- 避免：中文路径、重名覆盖、特殊字符、路径穿越

### PDF 四层校验

```python
# storage.py — validate_pdf()
1. 文件扩展名 .pdf
2. Content-Type application/pdf
3. Magic bytes %PDF-（文件头前 5 字节）
4. 文件大小 ≤ MAX_UPLOAD_SIZE_MB (默认 100 MB)
```

文件按 1 MB chunk 读取，超过上限即中止，避免先把超大文件完整读入内存。物理文件写入通过线程执行，不阻塞 FastAPI event loop；所有文件路径均被限制在 `STORAGE_DIR` sandbox 内。

### 异常补偿与事务边界

```python
# PaperService.import_pdf()
content = await validate_pdf(file)              # 1. 流式校验
saved_path = await save_bytes(content, "pdfs") # 2. UUID 存储

try:
    paper = await self.repo.create(...)         # 3. 创建 Paper
    await self.doc_repo.create(...)             # 4. 创建 Document
    await self.db.commit()                      # 5. 显式最终提交
except Exception:
    await self.db.rollback()                    # 6. 回滚 DB
    saved_path.unlink()                         # 7. 补偿：包含 commit 失败
    raise
```

上传服务在 `commit()` 成功前不会返回。任何创建、flush 或最终 commit 失败都会回滚数据库并清理刚写入的 PDF，避免孤儿文件。

### S7-A：PDF Parser Pipeline & Parse State

迁移 `d3f7a2e9c5b4_document_parser_lifecycle` 将 Document 解析状态统一为 `pending | processing | ready | failed`，并新增 `parser_version`、`ix_documents_parse_status` 与数据库 CHECK 约束。

```text
POST /api/documents/{document_id}/parse
GET  /api/documents/{document_id}/parse-status
```

解析服务会先执行用户归属校验，再用条件更新阻止同一 Document 并发解析；PyMuPDF 使用 `page.get_text("text")` 提取页级文本、尺寸与扫描页 warning。S7-A 仅更新 Document 的页数、状态、错误、解析时间与 parser version：不会修改原 PDF、`Document.file_path`、Paper metadata、Section 或 Chunk。失败会保留源文件和任何未来派生数据，并可调用同一 endpoint 重试。上传完成后前端会异步发起解析，不阻塞上传响应；Reader 显示解析状态，并在待解析或失败时提供触发/重试入口。

---

## 数据库迁移与质量检查

数据库 schema 的唯一演化入口是 Alembic。Docker 后端启动时会自动执行 `alembic upgrade head`；已有 S1-S3 本地数据库已标记到初始基线 `c0491cb1a8b2`，不重建表也不修改既有论文数据。

```bash
# 在 backend/ 下执行
alembic current
alembic upgrade head
alembic check

# 使用隔离数据库运行后端测试（不会触碰主库）
TEST_DATABASE_URL=postgresql+asyncpg://paper:paper123@localhost:5432/paper_workspace_test pytest -q

# 在 frontend/ 下执行
npm run lint
npm run build
```

搜索 API 通过 `Chunk -> Document -> Paper` 正确关联正文片段，并经 `Paper.user_id` 统一隔离；路由层仅调用 `SearchService`，不再包含重复 SQL 或静默吞异常逻辑。

---

## S5.5 元数据管理与 Library 检索

### 原子论文元数据保存

编辑器使用单一 aggregate endpoint，而不是依次发送多组更新请求：

```text
PUT /api/papers/{paper_id}/metadata
  → 标量 metadata + Authors + Tags + manual Keywords + Folders
  → 一个事务边界内提交，任一步失败则整体回滚
```

现有 `PATCH /papers/{id}` 及 Authors/Tags/Keywords/Folders replacement 端点继续保留，适用于未来局部操作。`PaperKeyword` 区分 `manual`、`metadata`、`pdf`、`ai` 来源；编辑器只替换 `manual`，不会清除解析或 AI 来源。

### Library 搜索与筛选

`GET /api/papers/` 是论文级 collection query：`q` 同时覆盖标题、摘要、作者姓名、Tag 名称、Keyword、DOI、arXiv ID、期刊、会议和出版商。关系表通过 `EXISTS` 子查询匹配，确保任意关联命中都只返回一条 Paper，`total` 和分页也按 Paper 计数。

```bash
curl "http://localhost:8000/api/papers/?q=federated&tag_id=<tag-uuid>&year=2025&status=ready&page=1&page_size=20"
```

支持参数：

| 参数 | 含义 |
|---|---|
| `q` | 论文级元数据关键词搜索 |
| `tag_id` / `folder_id` | 分类筛选 |
| `year` | 发表年份 |
| `starred` | 是否仅收藏（`true`） |
| `status` | 处理状态：`imported` / `processing` / `ready` / `failed` |
| `page` / `page_size` | 分页；`page_size` 支持 10 / 20 / 50 / 100 |

Library 前端将所有上述条件存入 URL；搜索和任一筛选变化自动重置至第一页，浏览器前进/后退与复制链接均可恢复当前查询。

---

## API 使用示例

所有 API 前缀为 `/api`。当前为单用户模式，无需认证。

### 论文管理

**创建论文（含作者、标签、文件夹）**

```bash
curl -X POST http://localhost:8000/api/papers/ \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Attention Is All You Need",
    "abstract": "The dominant sequence transduction models are based on complex recurrent or convolutional neural networks...",
    "doi": "10.5555/3295222.3295349",
    "arxiv_id": "1706.03762",
    "conference": "NeurIPS",
    "publication_year": 2017,
    "citation_count": 100000,
    "authors": [
      {"name": "Ashish Vaswani", "orcid": "0000-0003-2474-1798"},
      {"name": "Noam Shazeer", "affiliation": "Google Brain"}
    ],
    "tag_ids": ["<tag-uuid-1>"],
    "folder_ids": ["<folder-uuid-1>"]
  }'
```

**上传 PDF（创建 Paper + Document）**

```bash
curl -X POST http://localhost:8000/api/papers/upload \
  -F "file=@paper.pdf"
```

校验规则：文件名 `.pdf` 后缀 + Content-Type `application/pdf` + magic bytes `%PDF-` + 最大 100 MB。

返回的 Paper 包含 `document` 字段：

```json
{
  "id": "...",
  "title": "paper",
  "status": "imported",
  "document": {
    "id": "<document-uuid>",
    "original_filename": "paper.pdf",
    "file_size": 4218213,
    "mime_type": "application/pdf",
    "parse_status": "pending"
  }
}
```

**分页列表（支持筛选）**

```bash
# 全部
curl "http://localhost:8000/api/papers/?page=1&page_size=20"

# 搜索
curl "http://localhost:8000/api/papers/?q=federated&page=1"

# 按标签筛选
curl "http://localhost:8000/api/papers/?tag_id=<tag-uuid>"

# 按年份 + 星标
curl "http://localhost:8000/api/papers/?year=2025&starred=true"
```

响应格式：

```json
{
  "items": [
    {
      "id": "...",
      "title": "FedLDR: ...",
      "publication_year": 2025,
      "journal": "Neurocomputing",
      "status": "imported",
      "is_starred": false,
      "created_at": "2025-01-01T00:00:00",
      "first_author": "Yu Yang",
      "tags": [{"id": "...", "name": "Federated Learning", "color": null}],
      "has_document": false
    }
  ],
  "page": 1,
  "page_size": 20,
  "total": 5,
  "total_pages": 1
}
```

> `has_document` 为 `true` 表示有 PDF 附件，前端据此显示 PDF 图标。

**获取详情（含 document 信息）**

```bash
curl http://localhost:8000/api/papers/<paper_id>
```

**更新论文**

```bash
curl -X PATCH http://localhost:8000/api/papers/<paper_id> \
  -H "Content-Type: application/json" \
  -d '{"title": "Updated Title", "doi": "10.1234/new-doi"}'
```

> 修改 doi/arxiv_id/title/publication_year 时会自动做重复检测（排除自身）。

**删除论文**

```bash
curl -X DELETE http://localhost:8000/api/papers/<paper_id>
```

> 先 commit 数据库，后删物理文件。文件路径从 Document.file_path 读取。文件删除失败不影响数据一致性。

**星标（幂等）**

```bash
# 收藏
curl -X PUT http://localhost:8000/api/papers/<paper_id>/star

# 取消收藏
curl -X DELETE http://localhost:8000/api/papers/<paper_id>/star
```

### Document 文件访问

**获取文档元数据**

```bash
curl http://localhost:8000/api/documents/<document_id>
```

**获取 PDF 文件（浏览器内联展示）**

```bash
curl http://localhost:8000/api/documents/<document_id>/file -o paper.pdf
```

或直接在浏览器中打开：

```html
<iframe src="/api/documents/{document_id}/file" width="100%" height="800px"></iframe>
```

响应头：
- `Content-Type: application/pdf`
- `Content-Disposition: inline` — 浏览器内联展示，不触发下载

> S4 的 PDF.js 将直接消费此端点。
> 用户隔离：即使知道 document UUID，也无法访问其他用户的文件。

### Tag / Folder 管理（论文维度）

```bash
# 给论文加标签
curl -X POST http://localhost:8000/api/papers/<paper_id>/tags/<tag_id>

# 从论文移除标签
curl -X DELETE http://localhost:8000/api/papers/<paper_id>/tags/<tag_id>

# 加入文件夹
curl -X POST http://localhost:8000/api/papers/<paper_id>/folders/<folder_id>

# 移出文件夹
curl -X DELETE http://localhost:8000/api/papers/<paper_id>/folders/<folder_id>
```

### Tag 管理（独立维度）

```bash
# 列出标签（含 paper_count）
curl http://localhost:8000/api/tags/

# 创建标签
curl -X POST http://localhost:8000/api/tags/ \
  -H "Content-Type: application/json" \
  -d '{"name": "Transformer"}'

# 重命名
curl -X PATCH http://localhost:8000/api/tags/<tag_id> \
  -H "Content-Type: application/json" \
  -d '{"name": "Transformers"}'

# 删除
curl -X DELETE http://localhost:8000/api/tags/<tag_id>
```

### Folder 管理（独立维度）

```bash
# 列出文件夹
curl http://localhost:8000/api/folders/

# 创建文件夹
curl -X POST http://localhost:8000/api/folders/ \
  -H "Content-Type: application/json" \
  -d '{"name": "强化学习", "icon": "folder"}'
```

---

## 前端使用示例

### TypeScript 类型

```typescript
// frontend/src/features/paper/types.ts
interface DocumentBrief {
  id: string;
  original_filename: string | null;
  file_size: number | null;
  mime_type: string | null;
  parse_status: string;
}

interface Paper {
  id: string;
  title: string;
  doi?: string | null;
  status: "imported" | "processing" | "ready" | "failed";
  is_starred: boolean;
  authors: Author[];
  tags: TagBrief[];
  document?: DocumentBrief | null;  // S3 新增
  // ...
}

interface PaperListItem {
  id: string;
  title: string;
  // ...
  has_document?: boolean;  // S3 新增：是否有 PDF 附件
}
```

### PDF 上传（带进度）

```typescript
import { useUploadPaper } from "@/features/paper/hooks";

const uploadMut = useUploadPaper();

await uploadMut.mutateAsync({
  file: selectedFile,
  onProgress: (progress) => {
    console.log(`${progress}%`);  // 0 ~ 100
  },
});

// 上传成功后自动 invalidate papers query → Library 自动刷新
```

### 构建 Document 文件 URL

```typescript
import { getDocumentFileUrl } from "@/features/paper/api";

// 用于 PDF.js 或 <iframe>
const url = getDocumentFileUrl(documentId);
// → "/api/documents/{documentId}/file"
```

### React Query Hook 用法

```typescript
import { usePapers, useStarPaper, useCreatePaper, useUploadPaper } from "@/features/paper/hooks";

// 列表（自动分页 + URL 参数筛选）
const { data, isLoading } = usePapers({
  q: searchQuery,
  tag_id: selectedTagId,
  page: 1,
  page_size: 20,
});

// 星标（幂等 mutation）
const starMutation = useStarPaper();
starMutation.mutate(paperId);

// 创建论文
const createMutation = useCreatePaper();
createMutation.mutate({
  title: "Attention Is All You Need",
  doi: "10.5555/3295222.3295349",
  authors: [{ name: "Ashish Vaswani" }],
  tag_ids: [tagId1],
});

// 上传 PDF（带进度，成功后自动刷新列表）
const uploadMutation = useUploadPaper();
uploadMutation.mutate({ file, onProgress });
```

### Import Modal

前端提供了拖拽上传组件（`ImportModal`）：

```tsx
import { ImportModal } from "@/components/ImportModal";

<ImportModal onClose={() => setShowImportModal(false)} />
```

功能：
- 拖拽 PDF 到上传区域
- 点击选择文件
- 前端预校验（类型 + 大小）
- 上传进度条
- 状态管理：idle → selected → uploading → success / error
- 多文件批量上传
- 成功后 React Query 自动刷新 Library

### PaperCard PDF 指示器

PaperCard 根据 `has_document` 显示不同图标：
- 有 PDF：`FileType` 图标（主题色）+ "有 PDF" 标签
- 无 PDF：`FileText` 图标（灰色）

### 稳定颜色生成

前端为 Tag 和 Folder 生成基于名称 hash 的固定颜色（`getStableColor(name)`），避免后端硬编码颜色。

---

## S6-A：Reading Progress

阅读进度独立于 `Paper`，以具体 PDF 的 `Document` 为归属单位：同一篇论文将来拥有不同版本 PDF 时，每份文档可分别恢复页码。

- `ReadingProgress` 使用唯一约束 `UNIQUE(user_id, document_id)`，并在 User 或 Document 删除时由外键级联清理。
- `GET /api/papers/{paper_id}/reading-progress?document_id=<document_id>` 读取当前用户对指定 PDF 的进度；无记录时返回 `null`。
- `PUT /api/papers/{paper_id}/reading-progress` 以 `document_id`、`current_page`、`total_pages` 原子 upsert。服务端验证 Paper、Document 和用户归属关系，并计算 `progress_ratio`；页码必须满足 `1 <= current_page <= total_pages`。
- Reader 在 PDF 页数可用后只恢复一次；恢复完成前不会写入初始页码。随后翻页以 1 秒防抖持久化，页面进入后台、离开阅读器或切换论文时会立即 flush。
- S6-A 暂不计算活跃阅读时长；`reading_time_seconds` 仅作为后续活跃会话统计的预留字段。

### S6-B：Recent Reading + Continue Reading

`GET /api/reading/recent?limit=5` 从 `ReadingProgress` 聚合当前用户最近持久化的具体 PDF 进度，按 `last_read_at DESC, id DESC` 排序。每条记录保留 `paper` 基础信息、精确 `document.id`、页码、后端计算的比例和最近阅读时间；同一篇 Paper 的不同 PDF 保留为独立记录，确保继续阅读进入正确版本。

- Library 顶部展示最多 5 条最近阅读，含页码、比例、进度条、相对时间和空状态。
- “继续阅读”仅导航至 `/reader/{paper_id}?document_id={document_id}`；Reader 仍是恢复页码的唯一来源。
- Paper detail 同时返回向后兼容的 `document` 与稳定排序的 `documents` 列表，Reader 仅接受属于该 Paper 的 URL `document_id`，否则回退到默认 PDF。
- Annotation 查询也按 active `document_id` 筛选，避免多 PDF Paper 的不同 Evidence Anchor 混入同一 Reader 会话。

### S6-C：Reading Status

阅读工作流状态独立存储在 `Paper.reading_status`，与处理状态 `Paper.status` 完全分离：

```text
status            = imported / processing / ready / failed
reading_status    = unread / reading / finished / archived
```

- 新论文默认 `unread`；迁移 `b8e5f1c4d2a7_paper_reading_status` 为历史 Paper 回填 `unread`，并增加索引和数据库 CHECK 约束。
- `PUT /api/papers/{paper_id}/reading-status` 仅更新论文级阅读状态，服务层验证当前用户拥有该 Paper；用户可以在四个状态间手动切换。
- 首次成功持久化某份 PDF 进度时，后端在同一事务内仅作条件更新 `unread → reading`。`finished` 与 `archived` 永不因进度写入降级；到达最后一页也不会自动标记已读。
- Reader Toolbar 提供轻量阅读状态选择器。状态 mutation 与首次 progress 自动流转都会刷新 Paper 和 Library 缓存。
- Library 使用独立 URL 参数 `reading_status=unread|reading|finished|archived`；可与处理状态组合，例如 `?status=ready&reading_status=reading`。Paper Card 同时展示处理状态和阅读状态 badge。

### Annotation Document Anchor Hotfix

迁移 `a9d4e7b2c6f1_annotation_document_anchor_alignment` 以 fail-fast 方式收紧 Evidence Anchor 的数据库约束：先检查空 `document_id` 和错误的 Paper/Document 配对，只有数据完整时才将 `annotations.document_id` 对齐为 `NOT NULL`、`FOREIGN KEY ... ON DELETE CASCADE` 并创建 `ix_annotations_document_id`。不修改历史迁移，不会猜测回填或静默删除标注数据。

### S7-A：PDF Parser Pipeline & Parse State

迁移 `d3f7a2e9c5b4_document_parser_lifecycle` 将 Document 解析状态统一为 `pending | processing | ready | failed`，并新增 `parser_version`、`ix_documents_parse_status` 与数据库 CHECK 约束。

```text
POST /api/documents/{document_id}/parse
GET  /api/documents/{document_id}/parse-status
```

解析服务会先执行用户归属校验，再用条件更新阻止同一 Document 并发解析；PyMuPDF 使用 `page.get_text("text")` 提取页级文本、尺寸与扫描页 warning。S7-A 仅更新 Document 的页数、状态、错误、解析时间与 parser version：不会修改原 PDF、`Document.file_path`、Paper metadata、Section 或 Chunk。失败会保留源文件和任何未来派生数据，并可调用同一 endpoint 重试。上传完成后前端会异步发起解析，不阻塞上传响应；Reader 显示解析状态，并在待解析或失败时提供触发/重试入口。

### S7-B：Section + Section-aware Chunk

迁移 `e4b8c6a1f9d3_structured_document_derivatives` 演进既有 `sections`/`chunks` 表，不创建 v2 表：Section 增加时间字段，Chunk 增加 `page_start/page_end/char_count`，并以 `(document_id, chunk_index)` 保证文档内顺序唯一。解析服务现在采用：

```text
PDF → ParsedDocument（含 text spans）
   → SectionDetector（保守标题、层级、页码、Full Text fallback）
   → SectionChunker（段落感知、章节边界、页码追踪）
   → validate
   → 原子替换旧 Section/Chunk
```

`GET /api/documents/{document_id}/sections` 返回扁平、稳定顺序且经过用户隔离的 Section 列表；Chunk 暂不公开 API。Reader 左侧提供“PDF 目录 / 解析结构”切换，可跳转到 Section 起始页。无文本扫描 PDF 不产生空 Chunk；解析失败或派生数据校验失败不会删除旧结构。S7-B 不处理 Reference、Figure/Table，也不修改 Paper metadata。

### S7-C：Reference Extraction

迁移 `f6c2a9e7b4d1_document_references` 增加 PDF 派生 `Reference`：它严格归属于 `Document`，不会自动创建 Library Paper。`document_id` 使用 `ON DELETE CASCADE`，可选的 `matched_paper_id` 使用 `ON DELETE SET NULL`；`UNIQUE(document_id, order_index)` 防止重解析累积。

解析器只消费已识别的 `references` Section，不扫描 References 之后的 Appendix 或 checklist。分段支持编号、多行、跨页条目及无编号 author-year fallback；DOI/arXiv 优先规范化提取，title/authors/year/venue 均为 best-effort，无法可靠识别时保持空值。库内匹配仅按当前用户范围执行 DOI exact → arXiv exact → normalized title exact，不创建 `PaperRelation`。

`DerivedDocumentSnapshot` 统一包含 Sections、Chunks、References；三者先在内存校验，再在同一事务中 child-first 替换。`GET /api/documents/{document_id}/references` 经过 Document → Paper → current user 归属校验，Reader 左侧“参考文献”入口支持跳转来源页和打开已匹配的库内论文。

### S7-D：Figure / Table Metadata Extraction

迁移 `a7d3f9c2e5b6_document_elements` 增加统一的 PDF 派生 `DocumentElement`，第一版仅允许 `figure | table`。每个元素保存文档级稳定顺序、页码、可选 Section、label、caption、raw_text、来源与置信度；`UNIQUE(document_id, order_index)` 防重复。bbox 使用 Annotation 一致的 normalized `x/y/width/height` 协议；无法可靠定位视觉区域时四项都为 `NULL`，不会生成整页框。

ElementDetector 采用 caption-first 策略：识别 Figure/Fig./Table/图/表，合并邻近的多行 caption，并以 PDF image/vector 几何信息作为 Figure 向上、Table 向下的可选 bbox 证据。章节编号与新 caption 会终止合并，避免正文标题污染 caption。它不执行 OCR、AI 解释、表格单元格还原、图片裁剪，也不自动创建用户 Annotation。

Elements 纳入同一 `DerivedDocumentSnapshot`，替换顺序为 Elements → References → Chunks → Sections，再插入新快照；任一检测或校验异常都会保留旧快照。`GET /api/documents/{document_id}/elements?element_type=figure|table` 经过用户隔离，Reader “图表”入口按 Figures/Tables 展示并跳转页码。

### S8-A：Unified Search Contract + Paper-level Aggregation

`GET /api/search?q=...&page=1&page_size=20` 现在返回稳定的 Paper-level contract：一篇 Paper 永远只对应一个搜索结果，`total` 为命中 Paper 数，分页在 hit 聚合之后执行。内部统一使用 `SearchHit`，来源固定为 title/abstract/author/tag/keyword/doi/arxiv/journal/conference/publisher/section/chunk/reference/figure/table。

搜索由 Metadata、Section、Chunk、Reference、Element 五类 provider 分别产生 hit，再按 `paper_id` 聚合。首版权重只用于稳定排序，每篇 Paper 最多返回 5 条按来源权重和页码排序、经简单文本 fingerprint 去重的 matches，同时通过 `match_count` 保留完整命中数。所有派生 provider 均经 Document → Paper 的 user scope 隔离；本阶段只使用 PostgreSQL `ILIKE`，未引入 FTS、`pg_trgm`、embedding、semantic search、RRF、reranker、query expansion 或 AI search。

### S8-B：Search Quality, Query Capability & Performance

S8-A 的 Paper-level API contract 与前端 DTO 保持不变。查询现在统一进行空白折叠、case normalization、DOI/arXiv 前缀清理与识别；少于两个字符的普通查询直接拒绝。DOI/arXiv 使用 Paper/Reference 精确 shortcut，避免无意义全文扫描。

短元数据（论文标题、作者、Tag、Keyword、期刊、会议、出版社）使用 `pg_trgm` 支持 exact、prefix 与 fuzzy 命中；DOI/arXiv 不依赖 trigram。Chunk、Section、Reference 与 Figure/Table caption 使用 `simple` dictionary 的 generated `tsvector`、GIN 和 `websearch_to_tsquery`，多词查询采用 AND-like websearch 语义。后端 snippet 始终为最多约 240 字符的纯文本上下文，不包含 HTML。

Provider 将 exact/prefix/fuzzy/fulltext 分数归一化到 0–1；Paper 排序采用最佳加权命中、来源多样性奖励与封顶的次级命中奖励，避免长论文凭大量弱 Chunk 命中支配排名。同分继续按最佳来源、`updated_at` 和 Paper ID 确定性排序。Paper 与 authors 仍批量读取，不存在逐结果 N+1。

隔离规模门禁覆盖 100 Papers、1,000 Sections、5,000 Chunks、2,000 References；`EXPLAIN ANALYZE` 脚本位于 `backend/tests/search_explain.sql`。在该小型全内存夹具上 PostgreSQL 可合理选择亚毫秒 Seq Scan；关闭 Seq Scan 的索引资格检查确认 title trigram 以及 Chunk/Section/Reference GIN 谓词均产生 Bitmap Index Scan。

### S9-A：Markdown Note Aggregate

旧 `Note` 表已原位演进：正文唯一事实来源为 `content_markdown`，`paper_id` 可空，`note_type` 限定为 `general | paper | research`。所有 CRUD、详情与 Paper 范围查询均按当前 `user_id` 隔离；关联 Paper 时必须验证所有权。`PUT /api/notes/{id}` 原子保存完整 Note aggregate，同时保留 PATCH 供简单字段更新。

Notes 前端已移除 mock 数据，支持 `/notes`、`/notes/{noteId}` 和 `/papers/{paperId}/notes`。编辑器使用 Markdown source + 安全预览，支持 GFM、行内/块级 KaTeX，默认不执行原始 HTML；内容在停止输入 1 秒后自动保存，并以本地 revision 防止保存途中继续输入导致新内容被旧响应覆盖。S9-A 不包含 Evidence Linking、Structured Research Note 或 Note Search，这些分别留给 S9-B/C/D。

### S9-B：Evidence Linking

新增独立 `NoteEvidence` 关系表，将用户 Annotation 作为唯一 Evidence Anchor。每条关系保存稳定 `order_index` 和首次绑定时的 `quote_snapshot`；Note 与 Annotation 任一方删除都只级联关系，不会删除另一端内容。Paper-scoped Note 只能引用同一 Paper 的 Annotation，General Note 可以引用当前用户不同 Paper 的 Annotation，foreign user Annotation 永远拒绝。

主契约 `PUT /api/notes/{note_id}/evidence` 在任何写入前批量验证全部 ID，按照请求顺序完整替换；重复 ID、foreign Annotation 或跨 Paper Annotation 都会整体失败并保留原集合。Reader 快捷操作使用共享验证 primitive 的幂等 POST/DELETE，`POST /api/notes` 也可携带 `annotation_ids`，实现新建 Paper Note 与首条证据的单事务写入。Note detail 通过 eager-load 一次返回 Evidence 与 Annotation brief，不产生逐 Annotation N+1。

Reader 的已保存 Annotation 卡片新增“添加到笔记”；可选择当前 Paper Note，或新建论文笔记并立即绑定。Note 页面新增 Evidence Panel，可查看类型、页码与快照、移除关系，并复用 `/reader/{paperId}?document_id=...&page=...` 跳回原文。Markdown 自动保存与 Evidence API 相互独立，不会覆盖关系操作。

### S9-C：Structured Research Notes

`research` 类型 Note 现在拥有独立的结构化聚合：`ResearchNoteProfile` 保存研究问题、方法、结论、局限与未来工作，`ResearchContribution` 和 `ResearchExperiment` 分别保存贡献与实验卡片。实验可通过 `ExperimentContribution` 关联其支撑的贡献；贡献和实验只能通过 `ContributionEvidence` / `ExperimentEvidence` 引用当前 Note 已有的 `NoteEvidence`，不会复制或重新定义 Evidence Anchor。

`GET /api/notes/{note_id}/research-profile` 返回当前结构化聚合（未创建时为 `null`），`PUT /api/notes/{note_id}/research-profile` 对 Profile、Contribution、Experiment 及其全部关系执行单事务完整替换。服务会在写入前批量校验 Note 类型、Paper 归属、client ID 引用和 Evidence 归属，任一无效引用都会整体回滚；删除结构化卡片不会删除 NoteEvidence、Annotation 或 Markdown 正文。

Notes 页面为研究笔记提供“正文 / 结构化”双视图。结构化编辑器支持 Profile 字段、贡献与实验卡片、Evidence 选择以及实验到贡献的关联，并沿用 revision-aware 自动保存。Markdown aggregate 与 Research Profile 使用独立 API 和缓存键，保存任一视图都不会覆盖另一视图。

### S9-D：Note Search + Reader Integration

Global Search 的稳定契约已扩展为 `SearchPaperResult | SearchNoteResult`，两类结果分别携带显式 `entity_type`，在 Paper/Note 聚合完成后统一按实体评分、排序和分页。Paper 搜索结果保持原有结构；General、Paper 与 Research Note 始终作为独立 Note result 返回，不会伪装或并入 Paper。Library 的 `GET /api/papers?q=` 契约未改变。

Note 标题和 Markdown 正文使用 `simple` 配置的 generated `tsvector` 与 GIN 索引，结果摘要通过轻量 `normalize_note_search_text()` 去除常见 Markdown/LaTeX 标记。结构化检索覆盖 Profile、Contribution 与 Experiment（包括 datasets、baselines 和 metrics）；来源会细分为研究问题、方法、创新点、实验、结论和我的思考。`NoteEvidence.quote_snapshot` 不作为 Note 正文检索源，避免与 Paper 原文重复命中。所有 provider 都显式通过 `Note.user_id` 隔离。

Search UI 现在区分“论文 / 笔记”实体；结构化命中打开 `/notes/{id}?view=structured`，普通命中打开 Note 正文。Reader 右侧新增当前 Paper 的关联笔记列表，因此双向链路为 `Reader → Note → Evidence → Reader`，但 Reader 不嵌入完整笔记编辑器。

### S10-A：Embedding Infrastructure

Chunk 与 Note 现在拥有独立、可重建的 embedding 生命周期字段：固定维度向量、`embedding_model`、`embedding_dimension`、基于实际 provider 输入计算的 `embedding_content_hash`，以及 `pending | processing | ready | failed` 状态和错误信息。Chunk 的输入为 Section title + Chunk content；Note 的输入为 title + 清理常见 Markdown/LaTeX 标记后的正文，明确不包含 Evidence snapshot 或 Structured Research Profile。

`EmbeddingProvider` 协议将业务服务与供应商 SDK 解耦，首个实现为 OpenAI-compatible HTTP provider。`EmbeddingLifecycleService` 按配置批量处理当前用户的 stale Chunk/Note，内容、模型、维度与 hash 均未变化时直接跳过；provider 失败只把当前批次标记为 failed，不回滚或覆盖主数据。新 Chunk 默认 pending，Note 标题或 Markdown 变化后也会在原事务内标为 pending；reparse 删除旧 Chunk 时其内嵌向量天然一并删除。

管理接口为 `POST /api/embeddings/rebuild` 与 `GET /api/embeddings/status`。不会在应用启动时扫描或调用 embedding 服务，也没有把 API key 写入数据库或 Workspace backup。S10-A 不改变 `/api/search`，Semantic Search、Hybrid/RRF 和 RAG Context 分别留给 S10-B/C/D。

### S10-B：Semantic Retrieval

`GET /api/search` 现在支持 `mode=lexical|semantic`，默认 lexical，因此 S8/S9 的调用和结果契约保持不变。Semantic mode 仅调用 Query Embedding、Chunk vector provider 与 Note vector provider，不调用 lexical providers，也不会静默降级。Query vector 不持久化，并且必须与当前 Workspace 的 model/dimension 完全一致；provider 不可用或维度错误时返回明确的 503。

Chunk 与 Note 的余弦距离计算、过滤、排序和 top-K 全部在 PostgreSQL 中完成。检索仅接受 `ready + current model + current dimension + non-null vector`，并显式通过 Paper/Note 的 `user_id` 隔离。每类 provider 默认取 50 个候选并应用可配置的低阈值；Chunk 仍聚合为 Paper、Note 仍聚合为 Note，最终继续按实体分页。内部 hit 使用 `retrieval_method=semantic`，但公开 source 仍为 `chunk` 或 `note_content`。

Chunk 与 Note 均新增 cosine HNSW partial index。索引资格已通过 `enable_seqscan=off` 的 EXPLAIN 验证，两类查询都产生对应 HNSW Index Scan。Search 页面新增 URL 驱动的“关键词 / 语义”切换，`mode=semantic` 可刷新、复制和前进后退恢复；结果卡和 Reader/Note 导航保持原契约。S10-B 不包含 Hybrid、RRF、reranker 或 RAG context。

### S10-C：Hybrid Retrieval + RRF

`mode=hybrid` 顺序执行既有 lexical 与 semantic 两条独立候选链；两侧各自完成 Paper/Note 实体聚合后，才以 `(entity_type, UUID)` 为稳定 key 做实体级 Reciprocal Rank Fusion。第一版使用等权标准公式 `1 / (60 + rank)`，不直接相加 lexical raw score 与 cosine similarity。候选池会随目标页深度增长并限制为最多 200 个实体，最终仍按融合后的 Paper/Note 统一列表分页。

融合采用 union 而非 intersection：只被一条链召回的实体不会丢失，同时出现在两条链中的实体获得双路排名贡献。两侧 matches 会合并并按 source/document/section/page/text 稳定去重，保留内容来源与 Reader 定位信息。纯函数 `rrf_fuse()` 记录 lexical/semantic rank provenance，并使用明确的 rank、entity type 与 UUID tie-break，重复查询顺序稳定。

响应可选返回 `retrieval` metadata。Semantic mode 的 provider failure 仍为 503；Hybrid mode 遇到相同故障则显式降级为 lexical，并返回 `semantic_available=false`，前端显示轻量警告。当前模型没有 ready vector 时返回 `semantic_index_ready=false`，与 provider 故障区分。Search UI 支持“关键词 / 语义 / 混合”三种 URL 模式，但默认仍为无外部依赖的 lexical。S10-C 不包含 RAG context assembly。

### S10-D：RAG Context Assembly

新增 `POST /api/rag/context`，将 Chunk/Note 粒度的 lexical、semantic 或 hybrid 候选组装为可追溯上下文包，不调用 LLM、不生成回答或 Prompt。RAG DTO 与 Search Card 完全解耦：`RAGCandidate` 保留 source-level rank，最终 `RAGSource` 明确区分 `paper_chunk` 与 `note`，并携带 Paper、Document、Section、页码、Note 及稳定 `source_key` provenance。

RAG retrieval 直接复用 PostgreSQL FTS、pgvector 与 RRF 公式，但融合发生在 `chunk:{id}` / `note:{id}` source 层而非 Search 的 Paper/Note entity 层。可选 `paper_id` 会在数据库查询阶段限制 Chunk 与 Paper Note，同时排除 General Note、其他 Paper 和其他用户数据。Semantic failure 规则与 Search 一致：semantic 模式返回 503，hybrid 显式降级 lexical。

纯 Python `RAGContextAssembler` 负责稳定去重、同 Document/Section 的保守相邻 Chunk window 合并、禁止跨 Section 合并、Library-wide Paper 多样性、最多 2 个 Note、单来源 cap、总 token budget 和确定性 formatter。Token 为近似估算，并包含 provenance header 开销；截断会同时标记 source 与整个 context。格式明确使用 `[SOURCE n | PAPER]` / `[SOURCE n | NOTE]`，防止后续模型混淆论文证据和用户解释。

Search 页面已适配 Paper 结果卡、来源徽标、snippet 和 Paper 级分页。可定位的 Section/Chunk/Reference/Figure/Table match 跳转到 `/reader/{paperId}?document_id={documentId}&page={pageStart}`。Reader 仅在当前 Paper scope 初始化时消费一次 URL page，优先级为 URL page → ReadingProgress → Page 1，后续翻页不受 URL 持续控制。

```bash
# 读取指定 PDF 的已保存进度
curl "http://localhost:8000/api/papers/<paper_id>/reading-progress?document_id=<document_id>"

# 写入或更新进度
curl -X PUT "http://localhost:8000/api/papers/<paper_id>/reading-progress" \
  -H "Content-Type: application/json" \
  -d '{"document_id":"<document_id>","current_page":8,"total_pages":14}'
```

---

## 项目结构

```
.
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── endpoints/       # 薄层 HTTP 路由
│   │   │   │   ├── papers.py    # 论文 CRUD + 上传
│   │   │   │   ├── documents.py # 文档元数据 + 文件访问
│   │   │   │   ├── tags.py
│   │   │   │   ├── folders.py
│   │   │   │   └── ...
│   │   │   └── router.py
│   │   ├── core/
│   │   │   ├── config.py        # 配置 (Pydantic Settings + MAX_UPLOAD_SIZE_MB)
│   │   │   ├── database.py      # 引擎 / Session / get_current_user_id()
│   │   │   ├── exceptions.py    # 业务异常 (Domain Error hierarchy)
│   │   │   ├── storage.py       # PDF 校验 + UUID 存储 + 文件管理
│   │   │   └── security.py      # JWT (预留)
│   │   ├── models/              # SQLAlchemy ORM 模型
│   │   │   ├── document.py       # Document (file metadata, parse_status)
│   │   │   ├── paper.py          # Paper (knowledge entity)
│   │   │   └── ...
│   │   ├── schemas/             # Pydantic 请求/响应模型
│   │   │   ├── document.py       # DocumentBrief + DocumentResponse
│   │   │   ├── paper.py          # PaperResponse (含 document 字段)
│   │   │   └── ...
│   │   ├── repositories/        # 数据访问层（带 user_id 隔离）
│   │   │   ├── paper_repository.py
│   │   │   └── document_repository.py  # 用户隔离查询 (JOIN Paper)
│   │   ├── services/            # 业务逻辑层（业务编排）
│   │   │   ├── paper_service.py      # import_pdf + 删除补偿
│   │   │   └── document_service.py   # 文件解析 + 用户隔离
│   │   ├── processors/          # PDF 解析 / Chunk / Embedding
│   │   ├── tasks/               # Celery 异步任务
│   │   ├── seed.py              # 幂等种子数据
│   │   └── main.py
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── app/                 # 路由 / 布局 / Provider
│   │   ├── pages/               # Dashboard / Library / Reader ...
│   │   ├── features/
│   │   │   └── paper/
│   │   │       ├── api.ts       # API 调用 + uploadPaper + getDocumentFileUrl
│   │   │       ├── hooks.ts     # React Query hooks (useUploadPaper)
│   │   │       └── types.ts     # TypeScript 类型 (DocumentBrief)
│   │   ├── components/          # PaperCard / ImportModal / Sidebar ...
│   │   │   ├── ImportModal/     # 拖拽上传 + 进度条 + 状态管理
│   │   │   └── ...
│   │   ├── stores/              # Zustand
│   │   └── services/
│   │       └── api.ts           # Axios 实例 (baseURL: /api)
│   ├── vite.config.ts
│   └── package.json
└── docker-compose.yml
```

---

## 环境变量

| 变量 | 默认值 | 说明 |
|---|---|---|
| `DATABASE_URL` | `postgresql+asyncpg://paper:paper123@localhost:5432/paper_workspace` | PostgreSQL 连接串 |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis 连接串 |
| `EMBEDDING_BASE_URL` | `https://api.openai.com/v1` | OpenAI-compatible embedding API 根地址 |
| `EMBEDDING_API_KEY` | 空 | Embedding secret，仅从环境读取 |
| `EMBEDDING_MODEL` | `text-embedding-3-small` | 当前 Workspace embedding 模型 |
| `EMBEDDING_DIMENSION` | `384` | 固定向量维度；变更需要迁移 |
| `EMBEDDING_BATCH_SIZE` | `32` | 每次 provider 请求的最大文本数 |
| `SEMANTIC_CANDIDATE_K` | `50` | 每个 semantic provider 的数据库候选数 |
| `SEMANTIC_MIN_SIMILARITY` | `0.30` | Semantic 初始余弦相似度下限 |
| `HYBRID_RRF_K` | `60` | Reciprocal Rank Fusion 的稳定常数 |
| `HYBRID_CANDIDATE_ENTITIES` | `50` | Hybrid 每条候选链的最小实体池 |
| `HYBRID_MAX_CANDIDATE_ENTITIES` | `200` | Hybrid 深分页候选池上限 |
| `RAG_CANDIDATE_K` | `40` | 每条 RAG retrieval 链的 source 候选数 |
| `RAG_DEFAULT_MAX_SOURCES` | `8` | 默认上下文来源上限 |
| `RAG_DEFAULT_TOKEN_BUDGET` | `6000` | 默认近似 token 预算 |
| `RAG_MAX_TOKEN_BUDGET` | `12000` | API 允许的最大上下文预算 |
| `RAG_MAX_CHUNK_SOURCE_TOKENS` | `1200` | 单个 Chunk/window 上限 |
| `RAG_MAX_NOTE_SOURCE_TOKENS` | `1000` | 单个 Note 上限 |
| `RAG_MAX_NOTE_SOURCES` | `2` | 默认 Note 来源数量上限 |
| `STORAGE_DIR` | `./storage` | 文件存储目录 |
| `MAX_UPLOAD_SIZE_MB` | `100` | PDF 上传最大大小 (MB) |
| `SECRET_KEY` | `change-this-in-production` | JWT 密钥 |
| `OPENAI_API_KEY` | (空) | AI / Embedding 用 |
| `EMBEDDING_MODEL` | `all-MiniLM-L6-v2` | 向量模型 |
| `CHUNK_SIZE` | `512` | PDF 分块大小 |
| `CHUNK_OVERLAP` | `64` | 分块重叠 |

---

## Docker 持久化

```yaml
# docker-compose.yml
volumes:
  pgdata:        # PostgreSQL 数据
  redisdata:    # Redis 数据
  storage_data:  # PDF 文件存储
```

| Volume | 容器路径 | 用途 |
|---|---|---|
| `pgdata` | `/var/lib/postgresql/data` | PostgreSQL 数据库 |
| `redisdata` | `/data` | Redis 持久化 |
| `storage_data` | `/app/storage` | PDF 文件 |

```bash
# 验证持久化
docker compose down
docker compose up -d
# 论文和 PDF 都应该还在
```

```bash
# 检查存储目录
docker compose exec backend ls -lh /app/storage/pdfs
# 应看到 UUID 命名的 PDF 文件，而非原始文件名
```

```bash
# 检查数据库中的 Document
docker compose exec db psql -U paper -d paper_workspace -c \
  "SELECT id, paper_id, original_filename, file_path, file_size, parse_status FROM documents;"
```

---

## 开发路线

| Sprint | 内容 | 状态 |
|---|---|---|
| S1 | 项目脚手架 + PostgreSQL + 基础 API | ✅ |
| S2 | Paper + Author + Folder + Tag CRUD | ✅ |
| S2.5 | 架构加固：三层分层、用户隔离、删除一致性、作者去重 | ✅ |
| S3 | PDF 上传 + 文件存储 + PDF 校验 + 文件访问 API | ✅ |
| S4 | PDF.js 阅读器 + 目录 | ✅ |
| S5 | Evidence 标注层（Highlight / Underline / Comment / Area） | ✅ |
| S4.5 | 本地 Workspace + Backup / Restore / Auto Protection | ✅ |
| S5.5-A | 数据约束 + replacement contracts | ✅ |
| S5.5-B | Paper Metadata Editor | ✅ |
| S5.5-C | Aggregate Transaction + Keyword Frontend + Tag Management UI | ✅ |
| S5.5-D | Library Metadata Search & Filters | ✅ |
| S6-A | Document-scoped Reading Progress + Reader 恢复/防抖同步 | ✅ |
| S6-B | Recent Reading + Continue Reading | ✅ |
| S6-C | Reading Status（unread / reading / finished / archived） | ✅ |
| S6 | Reading Workflow | ✅ |
| S7-A | PDF Parser Pipeline + Parse State | ✅ |
| S7-B | Section + Paragraph-aware Chunk + Atomic Replacement | ✅ |
| S7-C | Reference Extraction | ✅ |
| S7-D | Figure / Table Metadata | ✅ |
| S7 | PDF Parser + Section + Chunk + Reference / Figure / Table Extraction | ✅ |
| S8-A | Unified Search Contract + Paper-level Aggregation | ✅ |
| S8-B | Search Quality + PostgreSQL FTS + pg_trgm + Performance | ✅ |
| S8 | 全文搜索 | ✅ |
| S9-A | User-scoped Note Aggregate + Markdown/LaTeX Editor | ✅ |
| S9-B | Annotation → NoteEvidence → Note | ✅ |
| S9-C | Structured Research Notes | ✅ |
| S9 Core | Markdown + Evidence-backed Structured Research Notes | ✅ |
| S9-D | Note Search + Reader Integration | ✅ |
| S9 | Markdown + Evidence-backed Structured Research Notes | ✅ |
| S10-A | Versioned Chunk/Note Embedding Infrastructure | ✅ |
| S10-B | Semantic Retrieval | ✅ |
| S10-C | Hybrid Retrieval + RRF | ✅ |
| S10-D | RAG Context Assembly | ✅ |
| S10 | Semantic / Hybrid Retrieval + RAG Base | ✅ |
| S11 | AI Deep Reading | 下一步 |
| S12 | 论文关系 + 知识图谱 |

---

## S2.5 架构加固总结

| 问题 | 修复 |
|---|---|
| 删除文件发生在 DB commit 前 | Service 显式 `commit()` 后再删文件 |
| Update 不做重复检测 | 修改身份字段时重新检测，排除自身 (`exclude_paper_id`) |
| 同名多作者被 `dict[name]` 覆盖 | Repository 返回 `dict[str, list[Author]]`，按 affiliation 精确匹配 |
| 重复 Tag/Folder ID 校验误判 | Pydantic `field_validator` 去重 + Service 层 `dict.fromkeys` 二次去重 |
| Service 依赖 `HTTPException` | 新建 `app/core/exceptions.py` 业务异常，API 层转换 |
| ORCID 未规范化 | `normalize_orcid()` 统一提取 `0000-0002-1825-0097` 格式，非法返回 `None` |
| Upload 依赖不统一 | 统一使用 `Depends(get_paper_service)` |
| `PaperMapper` 无意义 `@dataclass` | 去掉 `@dataclass`，纯 static method class |
| `TagNotFoundError` 未导入 | 补充导入，避免运行时 `NameError` |
| `_ORCID_RE` dead code | 真正使用 `_ORCID_RE` 常量 |

---

## S3 PDF 上传与存储总结

| 功能 | 实现 |
|---|---|
| PDF 四层校验 | 扩展名 + Content-Type + magic bytes `%PDF-` + 100MB 大小限制 |
| UUID 文件存储 | `storage/pdfs/{uuid}.pdf`，原始文件名存 `Document.original_filename` |
| Document model 增强 | 新增 `original_filename`、`mime_type`，`file_size` 改为 `BigInteger` |
| DocumentRepository | 用户隔离查询（JOIN Paper.user_id），`get_by_id` + `get_by_paper` |
| DocumentService | `get_document()` + `get_document_file()` 返回 `(Document, Path)` |
| import_pdf 重构 | validate_pdf → UUID 存储 → create Paper + Document → 显式 commit → 失败时 rollback + 删除文件 |
| 文件访问 API | `GET /api/documents/{id}/file` — `Content-Disposition: inline` |
| PaperResponse 增强 | 新增 `document: DocumentBrief` 字段 |
| PaperListResponse 增强 | 新增 `has_document: bool` 字段 |
| 前端 ImportModal | 拖拽上传 + 进度条 + 前端预校验 + 状态管理 |
| 前端 useUploadPaper | React Query mutation，成功后自动刷新 Library |
| PaperCard PDF 指示器 | 根据 `has_document` 显示不同图标 |
| 删除路径迁移 | 从 `Document.file_path` 读取（非 `Paper.pdf_path`） |
| Paper/Document 边界 | `Document.file_path` 为权威源，`Paper.pdf_path` 保留兼容 |

---

## License

Personal project. All rights reserved.
