import { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { Upload, Search, LayoutGrid, List, Plus, X } from "lucide-react";
import { useDeletePaper, usePaper, usePapers, useStarPaper, useUnstarPaper, useCreatePaper } from "@/features/paper/hooks";
import { useRecentReading } from "@/features/reading/hooks";
import { RecentReadingList } from "@/features/reading/RecentReadingList";
import { useTags } from "@/features/tag/hooks";
import { useFolders } from "@/features/folder/hooks";
import { clearLibraryFilters, parseLibraryQuery, toPaperListParams, updateLibraryQuery } from "@/features/library/libraryQuery";
import { PaperList } from "@/components/PaperList";
import { PaperCard } from "@/components/PaperCard";
import { ImportModal } from "@/components/ImportModal";
import { EditPaperDialog } from "@/features/paper/components/EditPaperDialog";
import clsx from "clsx";
import type { PaperCreateInput, PaperListItem } from "@/features/paper/types";
import type { Folder } from "@/features/folder/types";
import { getStableColor } from "@/utils";
import { useIdentityCandidates, useMyPaperStats, useResearchIdentity, useSetResearchIdentity } from "@/features/research-identity/hooks";

export default function Library() {
  const [searchParams, setSearchParams] = useSearchParams();
  const query = useMemo(() => parseLibraryQuery(searchParams), [searchParams]);

  const [view, setView] = useState<"list" | "grid">("list");
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showImportModal, setShowImportModal] = useState(false);
  const [editingPaperId, setEditingPaperId] = useState<string | null>(null);
  const [recentReadingExpanded, setRecentReadingExpanded] = useState(false);

  const { data: tags } = useTags();
  const { data: folders } = useFolders();
  const identity = useResearchIdentity();
  const identityCandidates = useIdentityCandidates();
  const myStats = useMyPaperStats();
  const setIdentity = useSetResearchIdentity();
  const editingPaper = usePaper(editingPaperId ?? undefined);

  const { data: paperPage, isLoading } = usePapers(toPaperListParams(query));
  const starMut = useStarPaper();
  const unstarMut = useUnstarPaper();
  const createPaperMut = useCreatePaper();
  const deletePaperMut = useDeletePaper();
  const { data: recentReading = [], isLoading: recentReadingLoading } = useRecentReading(recentReadingExpanded ? 10 : 2, true);

  const papers = paperPage?.items ?? [];

  const handleStarToggle = (paper: PaperListItem) => {
    if (paper.is_starred) {
      unstarMut.mutate(paper.id);
    } else {
      starMut.mutate(paper.id);
    }
  };

  const hasActiveFilters = Boolean(query.q || query.folder_id || query.tag_id || query.year || query.starred || query.status || query.reading_status || query.author_role || query.page_size !== 20);
  const updateFilter = (patch: Partial<typeof query>) => setSearchParams(updateLibraryQuery(searchParams, patch));
  const clearFilter = () => setSearchParams(clearLibraryFilters());

  return (
    <div className="w-full p-6">
      {/* Header */}
      <div className="mb-6 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <h1 className="text-xl font-semibold">我的论文</h1>
          {identity.data && myStats.data && (
            <span className="text-sm text-gray-400">{myStats.data.total} 篇 · 一作/共一 {myStats.data.first_or_co_first} · 通讯 {myStats.data.corresponding}</span>
          )}
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowCreateModal(true)}
            className="btn-ghost border border-gray-200"
          >
            <Plus className="h-4 w-4" />
            手动添加
          </button>
          <button
            onClick={() => setShowImportModal(true)}
            className="btn-primary"
          >
            <Upload className="h-4 w-4" />
            导入 PDF
          </button>
        </div>
      </div>

      {!identity.isLoading && !identity.data && <div className="mb-4 flex flex-wrap items-center gap-3 rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900 dark:border-amber-900 dark:bg-amber-950/30 dark:text-amber-100"><span>请先绑定“我的作者身份”，系统将按 Author ID 判断本人署名，避免同名误判。</span><select aria-label="我的作者身份" className="input h-9 min-w-56 bg-white text-sm" defaultValue="" onChange={(event)=>{if(event.target.value)setIdentity.mutate(event.target.value)}}><option value="" disabled>选择作者…</option>{identityCandidates.data?.map(candidate=><option key={candidate.author_id} value={candidate.author_id}>{candidate.name}{candidate.affiliation?` · ${candidate.affiliation}`:""}（{candidate.paper_count} 篇）</option>)}</select></div>}
      {identity.data && <div className="mb-4 flex items-center gap-2 text-xs text-gray-500">当前研究身份：<strong className="text-gray-700 dark:text-gray-200">{identity.data.author_name}</strong><select aria-label="切换我的作者身份" className="input h-8 w-auto text-xs" value={identity.data.author_id} onChange={(event)=>setIdentity.mutate(event.target.value)}>{identityCandidates.data?.map(candidate=><option key={candidate.author_id} value={candidate.author_id}>{candidate.name}{candidate.affiliation?` · ${candidate.affiliation}`:""}</option>)}</select></div>}

      <RecentReadingList
        items={recentReading}
        isLoading={recentReadingLoading}
        expanded={recentReadingExpanded}
        onToggleExpanded={() => setRecentReadingExpanded((expanded) => !expanded)}
      />

      {/* Toolbar */}
      <div className="mb-4 flex items-center gap-3">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
          <LibrarySearchInput key={query.q ?? ""} query={query.q} searchParams={searchParams} setSearchParams={setSearchParams} />
        </div>

        {hasActiveFilters && <button onClick={clearFilter} className="flex items-center gap-1 rounded-lg bg-primary-50 px-3 py-2 text-sm text-primary-600">清除筛选<X className="h-3 w-3" /></button>}

        <div className="flex items-center gap-1 rounded-lg border border-gray-200 p-1">
          <button
            onClick={() => setView("list")}
            className={clsx(
              "rounded p-1.5",
              view === "list" ? "bg-gray-100 text-gray-700" : "text-gray-400"
            )}
          >
            <List className="h-4 w-4" />
          </button>
          <button
            onClick={() => setView("grid")}
            className={clsx(
              "rounded p-1.5",
              view === "grid" ? "bg-gray-100 text-gray-700" : "text-gray-400"
            )}
          >
            <LayoutGrid className="h-4 w-4" />
          </button>
        </div>
      </div>

      <div className="mb-4 flex items-center gap-2 overflow-x-auto rounded-lg border border-gray-200 bg-gray-50 p-2 dark:border-slate-700 dark:bg-slate-800">
        <select aria-label="文件夹" className="input h-9 min-w-32 flex-1 text-sm" value={query.folder_id ?? ""} onChange={(event) => updateFilter({ folder_id: event.target.value || undefined })}><option value="">全部文件夹</option>{flattenFolders(folders ?? []).map((folder) => <option key={folder.id} value={folder.id}>{folder.name}</option>)}</select>
        <select aria-label="标签" className="input h-9 min-w-32 flex-1 text-sm" value={query.tag_id ?? ""} onChange={(event) => updateFilter({ tag_id: event.target.value || undefined })}><option value="">全部标签</option>{tags?.map((tag) => <option key={tag.id} value={tag.id}>{tag.name}</option>)}</select>
        <input aria-label="年份" className="input h-9 min-w-28 flex-1 text-sm" type="number" min="1000" max="9999" placeholder="全部年份" value={query.year ?? ""} onChange={(event) => updateFilter({ year: event.target.value ? Number(event.target.value) : undefined })} />
        <select aria-label="处理状态" className="input h-9 min-w-32 flex-1 text-sm" value={query.status ?? ""} onChange={(event) => updateFilter({ status: event.target.value as typeof query.status || undefined })}><option value="">全部处理状态</option><option value="imported">已导入</option><option value="processing">解析中</option><option value="ready">就绪</option><option value="failed">失败</option></select>
        <select aria-label="阅读状态" className="input h-9 min-w-32 flex-1 text-sm" value={query.reading_status ?? ""} onChange={(event) => updateFilter({ reading_status: event.target.value as typeof query.reading_status || undefined })}><option value="">全部阅读状态</option><option value="unread">未读</option><option value="reading">阅读中</option><option value="finished">已读</option><option value="archived">已归档</option></select>
        <label className="flex h-9 min-w-max items-center gap-2 rounded-lg border border-gray-200 bg-white px-3 text-sm text-gray-700 dark:border-slate-600 dark:bg-slate-900 dark:text-gray-200"><input type="checkbox" checked={Boolean(query.starred)} onChange={(event) => updateFilter({ starred: event.target.checked || undefined })} />仅收藏</label>
        <select aria-label="每页数量" title="每页数量" className="input h-9 w-24 shrink-0 text-sm" value={query.page_size} onChange={(event) => updateFilter({ page_size: Number(event.target.value) })}><option value="10">10 / 页</option><option value="20">20 / 页</option><option value="50">50 / 页</option><option value="100">100 / 页</option></select>
      </div>

      {/* Papers */}
      <div className="mb-4 flex gap-2" aria-label="我的作者身份筛选">{([ [undefined,"全部"], ["first","第一/共同一作"], ["corresponding","通讯作者"], ["other","其他署名"] ] as const).map(([role,label])=><button key={role??"all"} type="button" className={clsx("rounded-full px-3 py-1.5 text-xs",query.author_role===role?"bg-primary-500 text-white":"bg-gray-100 text-gray-600 dark:bg-slate-800 dark:text-gray-300")} onClick={()=>updateFilter({author_role:role})}>{label}</button>)}</div>
      {isLoading ? (
        <div className="flex justify-center py-20">
          <p className="text-sm text-gray-400">加载中...</p>
        </div>
      ) : papers.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-20 text-gray-400">
          <p className="text-sm">暂无论文</p>
          <p className="mt-1 text-xs">点击「导入 PDF」或「手动添加」开始</p>
        </div>
      ) : view === "list" ? (
        <PaperList
          papers={papers}
          onToggleStar={(id) => {
            const paper = papers.find((p) => p.id === id);
            if (paper) handleStarToggle(paper);
          }}
          onEdit={setEditingPaperId}
        />
      ) : (
        <div className="grid grid-cols-2 gap-4">
          {papers.map((paper) => (
            <PaperCard
              key={paper.id}
              paper={paper}
              onToggleStar={(id) => {
                const p = papers.find((p) => p.id === id);
                if (p) handleStarToggle(p);
              }}
              onEdit={setEditingPaperId}
            />
          ))}
        </div>
      )}

      {/* Pagination */}
      {paperPage && paperPage.total_pages > 1 && (
        <div className="mt-6 flex items-center justify-center gap-2">
          {Array.from({ length: paperPage.total_pages }, (_, i) => i + 1).map((pg) => {
            const newParams = updateLibraryQuery(searchParams, { page: pg }, false);
            return (
              <button
                key={pg}
                onClick={() => setSearchParams(newParams)}
                className={clsx(
                  "rounded px-3 py-1 text-sm",
                  pg === query.page
                    ? "bg-primary-500 text-white"
                    : "text-gray-600 hover:bg-gray-100"
                )}
              >
                {pg}
              </button>
            );
          })}
        </div>
      )}

      {editingPaperId && editingPaper.data && <EditPaperDialog paper={editingPaper.data} onClose={() => setEditingPaperId(null)} onDelete={async (paper) => { await deletePaperMut.mutateAsync(paper.id); }} />}
      {editingPaperId && editingPaper.isLoading && <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/50"><div className="rounded-lg bg-white px-4 py-3 text-sm shadow-lg dark:bg-slate-900">正在加载论文信息…</div></div>}

      {/* Import Modal */}
      {showImportModal && (
        <ImportModal onClose={() => setShowImportModal(false)} />
      )}

      {/* Create Paper Modal */}
      {showCreateModal && (
        <CreatePaperModal
          tags={tags || []}
          onClose={() => setShowCreateModal(false)}
          onSubmit={async (data) => {
            await createPaperMut.mutateAsync(data);
            setShowCreateModal(false);
          }}
        />
      )}
    </div>
  );
}

function LibrarySearchInput({ query, searchParams, setSearchParams }: { query?: string; searchParams: URLSearchParams; setSearchParams: ReturnType<typeof useSearchParams>[1] }) {
  const [value, setValue] = useState(query ?? "");
  useEffect(() => {
    const timer = setTimeout(() => {
      const normalized = value.trim() || undefined;
      if (normalized !== query) setSearchParams(updateLibraryQuery(searchParams, { q: normalized }), { replace: true });
    }, 300);
    return () => clearTimeout(timer);
  }, [value, query, searchParams, setSearchParams]);
  return <input type="text" placeholder="搜索标题、摘要、作者、标签、关键词、DOI 或出版信息..." value={value} onChange={(event) => setValue(event.target.value)} className="input pl-9" />;
}

function flattenFolders(folders: Folder[]): Folder[] {
  return folders.flatMap((folder) => [folder, ...flattenFolders(folder.children)]);
}

// ──────────────────────── Create Paper Modal ────────────────────────

interface CreatePaperModalProps {
  tags: { id: string; name: string; color: string | null }[];
  onClose: () => void;
  onSubmit: (data: PaperCreateInput) => Promise<void>;
}

function CreatePaperModal({ tags, onClose, onSubmit }: CreatePaperModalProps) {
  const [title, setTitle] = useState("");
  const [abstract, setAbstract] = useState("");
  const [doi, setDoi] = useState("");
  const [arxivId, setArxivId] = useState("");
  const [journal, setJournal] = useState("");
  const [conference, setConference] = useState("");
  const [year, setYear] = useState("");
  const [authors, setAuthors] = useState("");
  const [selectedTagIds, setSelectedTagIds] = useState<string[]>([]);

  const handleSubmit = async () => {
    if (!title.trim()) return;

    const authorList = authors
      .split(",")
      .map((s) => s.trim())
      .filter(Boolean)
      .map((name, idx) => ({ name, author_order: idx }));

    const data: PaperCreateInput = {
      title: title.trim(),
      abstract: abstract.trim() || undefined,
      doi: doi.trim() || undefined,
      arxiv_id: arxivId.trim() || undefined,
      journal: journal.trim() || undefined,
      conference: conference.trim() || undefined,
      publication_year: year ? parseInt(year) : undefined,
      authors: authorList,
      tag_ids: selectedTagIds,
    };

    await onSubmit(data);
  };

  const toggleTag = (tagId: string) => {
    setSelectedTagIds((prev) =>
      prev.includes(tagId) ? prev.filter((id) => id !== tagId) : [...prev, tagId]
    );
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30" onClick={onClose}>
      <div
        className="w-full max-w-lg rounded-xl bg-white p-6 shadow-xl max-h-[90vh] overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-lg font-semibold">添加论文</h2>
          <button onClick={onClose} className="rounded-lg p-1 text-gray-400 hover:bg-gray-100">
            <X className="h-5 w-5" />
          </button>
        </div>

        <div className="space-y-4">
          {/* Title */}
          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700">
              标题 <span className="text-red-500">*</span>
            </label>
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="FedLDR: Federated Learning..."
              className="input"
              autoFocus
            />
          </div>

          {/* Authors */}
          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700">作者</label>
            <input
              type="text"
              value={authors}
              onChange={(e) => setAuthors(e.target.value)}
              placeholder="Yu Yang, Zhi Chen, ...（逗号分隔）"
              className="input"
            />
          </div>

          {/* Year + Journal */}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">年份</label>
              <input
                type="number"
                value={year}
                onChange={(e) => setYear(e.target.value)}
                placeholder="2025"
                className="input"
              />
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">期刊</label>
              <input
                type="text"
                value={journal}
                onChange={(e) => setJournal(e.target.value)}
                placeholder="Neurocomputing"
                className="input"
              />
            </div>
          </div>

          {/* Conference */}
          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700">会议</label>
            <input
              type="text"
              value={conference}
              onChange={(e) => setConference(e.target.value)}
              placeholder="ICML, NeurIPS, ..."
              className="input"
            />
          </div>

          {/* DOI + arXiv */}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">DOI</label>
              <input
                type="text"
                value={doi}
                onChange={(e) => setDoi(e.target.value)}
                placeholder="10.xxxx/xxxx"
                className="input"
              />
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">arXiv ID</label>
              <input
                type="text"
                value={arxivId}
                onChange={(e) => setArxivId(e.target.value)}
                placeholder="2501.00001"
                className="input"
              />
            </div>
          </div>

          {/* Abstract */}
          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700">摘要</label>
            <textarea
              value={abstract}
              onChange={(e) => setAbstract(e.target.value)}
              placeholder="论文摘要..."
              rows={3}
              className="input resize-none"
            />
          </div>

          {/* Tags */}
          {tags.length > 0 && (
            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">标签</label>
              <div className="flex flex-wrap gap-1.5">
                {tags.map((tag) => (
                  <button
                    key={tag.id}
                    onClick={() => toggleTag(tag.id)}
                    className={clsx(
                      "rounded px-2 py-1 text-xs transition-colors",
                      selectedTagIds.includes(tag.id)
                        ? "text-white"
                        : "text-gray-600 border border-gray-200 hover:bg-gray-50"
                    )}
                    style={
                      selectedTagIds.includes(tag.id)
                        ? { backgroundColor: tag.color || getStableColor(tag.name) }
                        : undefined
                    }
                  >
                    {tag.name}
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Actions */}
        <div className="mt-6 flex justify-end gap-2">
          <button onClick={onClose} className="btn-ghost border border-gray-200">
            取消
          </button>
          <button
            onClick={handleSubmit}
            disabled={!title.trim()}
            className="btn-primary disabled:opacity-50 disabled:cursor-not-allowed"
          >
            创建
          </button>
        </div>
      </div>
    </div>
  );
}
