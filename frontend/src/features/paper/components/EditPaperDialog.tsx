import { AlertTriangle, LoaderCircle, Trash2, X } from "lucide-react";
import { useMemo, useState } from "react";

import { useFolders } from "@/features/folder/hooks";
import { useDeleteKeyword, useKeywords } from "@/features/keyword/hooks";
import { PaperKeywordSelector } from "@/features/keyword/components/PaperKeywordSelector";
import { useCreateTag, useDeleteTag, useTags, useUpdateTag } from "@/features/tag/hooks";
import type { Paper } from "../types";
import { useSavePaperMetadata } from "../hooks";
import { AuthorEditor } from "./AuthorEditor";
import { PaperFolderSelector } from "./PaperFolderSelector";
import { PaperTagSelector } from "./PaperTagSelector";

interface EditPaperDialogProps {
  paper: Paper;
  onClose: () => void;
  onDelete?: (paper: Paper) => Promise<void> | void;
}

type SaveFailure = { stage: "metadata"; error: unknown };

const STAGE_LABEL: Record<SaveFailure["stage"], string> = {
  metadata: "论文元数据",
};

const emptyToNull = (value: string) => value.trim() || null;
const asOptionalNumber = (value: string) => value.trim() === "" ? null : Number(value);

function messageFromError(error: unknown) {
  if (typeof error === "object" && error && "response" in error) {
    const detail = (error as { response?: { data?: { detail?: unknown } } }).response?.data?.detail;
    if (typeof detail === "string") return detail;
  }
  return error instanceof Error ? error.message : "请求未完成，请稍后重试。";
}

export function EditPaperDialog({ paper, onClose, onDelete }: EditPaperDialogProps) {
  const tags = useTags();
  const folders = useFolders();
  const keywords = useKeywords();
  const deleteKeyword = useDeleteKeyword();
  const createTag = useCreateTag();
  const updateTag = useUpdateTag();
  const deleteTag = useDeleteTag();
  const save = useSavePaperMetadata();
  const [title, setTitle] = useState(paper.title);
  const [abstract, setAbstract] = useState(paper.abstract ?? "");
  const [doi, setDoi] = useState(paper.doi ?? "");
  const [arxivId, setArxivId] = useState(paper.arxiv_id ?? "");
  const [url, setUrl] = useState(paper.url ?? "");
  const [journal, setJournal] = useState(paper.journal ?? "");
  const [conference, setConference] = useState(paper.conference ?? "");
  const [publisher, setPublisher] = useState(paper.publisher ?? "");
  const [year, setYear] = useState(paper.publication_year?.toString() ?? "");
  const [citationCount, setCitationCount] = useState(paper.citation_count?.toString() ?? "");
  const [authors, setAuthors] = useState<import("../types").AuthorInput[]>(paper.authors.map((author) => ({ name: author.name, orcid: author.orcid ?? "", affiliation: author.affiliation ?? "", is_co_first: Boolean(author.is_co_first), is_corresponding: Boolean(author.is_corresponding) })));
  const [tagIds, setTagIds] = useState(paper.tags.map((tag) => tag.id));
  const [folderIds, setFolderIds] = useState(paper.folders.map((folder) => folder.id));
  const [keywordInputs, setKeywordInputs] = useState(paper.keywords.filter((keyword) => keyword.sources.includes("manual")).map((keyword) => ({ name: keyword.display_name })));
  const [newTagName, setNewTagName] = useState("");
  const [newTagError, setNewTagError] = useState<string | null>(null);
  const [editingTagId, setEditingTagId] = useState<string | null>(null);
  const [editingTagName, setEditingTagName] = useState("");
  const [editingTagColor, setEditingTagColor] = useState("#6366f1");
  const [editingTagError, setEditingTagError] = useState<string | null>(null);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState<string | null>(null);

  const initial = useMemo(() => JSON.stringify({ title: paper.title, abstract: paper.abstract ?? "", doi: paper.doi ?? "", arxivId: paper.arxiv_id ?? "", url: paper.url ?? "", journal: paper.journal ?? "", conference: paper.conference ?? "", publisher: paper.publisher ?? "", year: paper.publication_year?.toString() ?? "", citationCount: paper.citation_count?.toString() ?? "", authors: paper.authors.map((author) => ({ name: author.name, orcid: author.orcid ?? "", affiliation: author.affiliation ?? "", is_co_first: Boolean(author.is_co_first), is_corresponding: Boolean(author.is_corresponding) })), tagIds: paper.tags.map((tag) => tag.id), folderIds: paper.folders.map((folder) => folder.id), keywordInputs: paper.keywords.filter((keyword) => keyword.sources.includes("manual")).map((keyword) => ({ name: keyword.display_name })) }), [paper]);
  const current = JSON.stringify({ title, abstract, doi, arxivId, url, journal, conference, publisher, year, citationCount, authors, tagIds, folderIds, keywordInputs });
  const dirty = initial !== current;
  const disabled = save.isPending || isDeleting;

  const requestClose = () => {
    if (dirty && !window.confirm("你有尚未保存的修改。确定放弃这些修改吗？")) return;
    onClose();
  };
  const createQuickTag = async () => {
    const name = newTagName.trim();
    if (!name) return;
    setNewTagError(null);
    try {
      const tag = await createTag.mutateAsync({ name });
      setTagIds((ids) => ids.includes(tag.id) ? ids : [...ids, tag.id]);
      setNewTagName("");
    } catch (error) {
      setNewTagError(messageFromError(error));
    }
  };
  const handleDelete = async () => {
    if (!onDelete || isDeleting) return;
    if (!window.confirm(`确定删除“${paper.title}”吗？这会移除论文记录、关联信息及其已导入的 PDF，且无法恢复。`)) return;
    setDeleteError(null);
    setIsDeleting(true);
    try {
      await onDelete(paper);
      onClose();
    } catch (error) {
      setDeleteError(messageFromError(error));
      setIsDeleting(false);
    }
  };
  const openTagEditor = (tag: import("@/features/tag/types").Tag) => {
    setEditingTagId(tag.id);
    setEditingTagName(tag.name);
    setEditingTagColor(tag.color || "#6366f1");
    setEditingTagError(null);
  };
  const saveEditedTag = async () => {
    if (!editingTagId || !editingTagName.trim()) return;
    setEditingTagError(null);
    try {
      await updateTag.mutateAsync({ tagId: editingTagId, data: { name: editingTagName.trim(), color: editingTagColor } });
      setEditingTagId(null);
    } catch (error) {
      setEditingTagError(messageFromError(error));
    }
  };
  const removeEditedTag = async () => {
    if (!editingTagId) return;
    const tag = tags.data?.find((item) => item.id === editingTagId);
    if (!window.confirm(`删除“${tag?.name ?? editingTagName}”不会删除论文，只会解除它与所有论文的关联。确定删除吗？`)) return;
    setEditingTagError(null);
    try {
      await deleteTag.mutateAsync(editingTagId);
      setTagIds((ids) => ids.filter((id) => id !== editingTagId));
      setEditingTagId(null);
    } catch (error) {
      setEditingTagError(messageFromError(error));
    }
  };
  const removeKeywordSuggestion = async (keyword: import("@/features/keyword/types").Keyword) => {
    if (!window.confirm(`永久删除关键词“${keyword.display_name}”吗？这会同时解除它与所有论文的关联，且无法恢复。`)) return;
    setSaveError(null);
    try {
      await deleteKeyword.mutateAsync(keyword.id);
    } catch (error) {
      setSaveError(`删除关键词失败：${messageFromError(error)}`);
    }
  };

  const handleSave = async () => {
    setSaveError(null);
    const parsedYear = asOptionalNumber(year);
    const parsedCitationCount = asOptionalNumber(citationCount);
    const currentYear = new Date().getFullYear() + 1;
    if (!title.trim()) return setSaveError("标题不能为空。");
    if (parsedYear !== null && (!Number.isInteger(parsedYear) || parsedYear < 1000 || parsedYear > currentYear)) return setSaveError(`年份需介于 1000 与 ${currentYear} 之间。`);
    if (parsedCitationCount !== null && (!Number.isInteger(parsedCitationCount) || parsedCitationCount < 0)) return setSaveError("引用次数必须是非负整数。");
    if (authors.some((author) => !author.name.trim())) return setSaveError("每位作者都必须填写姓名。");
    try {
      await save.mutateAsync({ paperId: paper.id, draft: {
        title: title.trim(), abstract: emptyToNull(abstract), doi: emptyToNull(doi), arxiv_id: emptyToNull(arxivId), url: emptyToNull(url), journal: emptyToNull(journal), conference: emptyToNull(conference), publisher: emptyToNull(publisher), publication_year: parsedYear, citation_count: parsedCitationCount,
        authors: authors.map((author) => ({ name: author.name.trim(), orcid: emptyToNull(author.orcid ?? ""), affiliation: emptyToNull(author.affiliation ?? ""), is_co_first: Boolean(author.is_co_first), is_corresponding: Boolean(author.is_corresponding) })), tag_ids: tagIds, folder_ids: folderIds, keywords: keywordInputs,
      } });
      onClose();
    } catch (failure) {
      const { stage, error } = failure as SaveFailure;
      setSaveError(`${STAGE_LABEL[stage]}保存失败：${messageFromError(error)}。本次变更未写入，页面已重新同步服务器状态。`);
    }
  };

  return <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/50 p-4" role="dialog" aria-modal="true" aria-label="编辑论文">
    <div className="flex max-h-[92vh] w-full max-w-4xl flex-col overflow-hidden rounded-xl bg-white shadow-xl dark:bg-slate-900">
      <div className="flex items-center justify-between border-b border-gray-200 px-6 py-4 dark:border-slate-700"><div><h2 className="font-semibold">编辑论文</h2><p className="mt-0.5 text-xs text-gray-500">更新论文元数据、作者和分类信息。</p></div><button type="button" className="btn-ghost p-1" aria-label="关闭编辑" onClick={requestClose} disabled={disabled}><X className="h-5 w-5" /></button></div>
      <div className="overflow-y-auto px-6 py-5"><div className="space-y-7">
        {saveError && <div className="flex gap-2 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700"><AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />{saveError}</div>}
        {deleteError && <div className="flex gap-2 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700"><AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />删除失败：{deleteError}</div>}
        <section className="space-y-3"><h3 className="text-sm font-semibold">基本信息</h3><label className="block text-sm"><span className="mb-1 block text-gray-600 dark:text-gray-300">标题 *</span><input className="input" value={title} disabled={disabled} onChange={(event) => setTitle(event.target.value)} /></label><label className="block text-sm"><span className="mb-1 block text-gray-600 dark:text-gray-300">摘要</span><textarea className="input min-h-28 resize-y" value={abstract} disabled={disabled} onChange={(event) => setAbstract(event.target.value)} /></label><div className="grid gap-3 md:grid-cols-2"><Field label="DOI" value={doi} disabled={disabled} onChange={setDoi} /><Field label="arXiv ID" value={arxivId} disabled={disabled} onChange={setArxivId} /></div><Field label="URL" value={url} disabled={disabled} onChange={setUrl} /></section>
        <section className="space-y-3"><h3 className="text-sm font-semibold">出版信息</h3><div className="grid gap-3 md:grid-cols-2"><Field label="年份" type="number" value={year} disabled={disabled} onChange={setYear} /><Field label="引用次数" type="number" value={citationCount} disabled={disabled} onChange={setCitationCount} /><Field label="期刊" value={journal} disabled={disabled} onChange={setJournal} /><Field label="会议" value={conference} disabled={disabled} onChange={setConference} /></div><Field label="出版商" value={publisher} disabled={disabled} onChange={setPublisher} /></section>
        <AuthorEditor authors={authors} disabled={disabled} onChange={setAuthors} />
        <PaperKeywordSelector value={keywordInputs} suggestions={keywords.data ?? []} disabled={disabled} deletingKeywordId={deleteKeyword.variables ?? null} onChange={setKeywordInputs} onDeleteSuggestion={(keyword) => void removeKeywordSuggestion(keyword)} />
        <PaperTagSelector tags={tags.data ?? []} selectedIds={tagIds} disabled={disabled || createTag.isPending || updateTag.isPending || deleteTag.isPending} onChange={setTagIds} onCreate={() => document.getElementById("quick-tag-name")?.focus()} onEdit={openTagEditor} />
        <div className="flex gap-2"><input id="quick-tag-name" className="input" placeholder="新标签名称" value={newTagName} disabled={disabled || createTag.isPending} onChange={(event) => setNewTagName(event.target.value)} onKeyDown={(event) => { if (event.key === "Enter") { event.preventDefault(); void createQuickTag(); } }} /><button type="button" className="btn-ghost border border-gray-200 text-sm" disabled={!newTagName.trim() || disabled || createTag.isPending} onClick={() => void createQuickTag()}>{createTag.isPending ? "创建中…" : "创建并选择"}</button></div>{newTagError && <p className="text-xs text-red-600">{newTagError}</p>}
        {editingTagId && <div className="rounded-lg border border-gray-200 bg-gray-50 p-3 dark:border-slate-700 dark:bg-slate-800"><div className="mb-2 flex items-center justify-between"><h4 className="text-sm font-medium">编辑标签</h4><button type="button" className="btn-ghost p-1" aria-label="关闭标签编辑" onClick={() => setEditingTagId(null)}><X className="h-4 w-4" /></button></div><div className="flex items-center gap-2"><input className="input h-9 flex-1 text-sm" aria-label="标签名称" value={editingTagName} disabled={updateTag.isPending || deleteTag.isPending} onChange={(event) => setEditingTagName(event.target.value)} /><input type="color" aria-label="标签颜色" className="h-9 w-12 cursor-pointer rounded border border-gray-200 bg-white p-1" value={editingTagColor} disabled={updateTag.isPending || deleteTag.isPending} onChange={(event) => setEditingTagColor(event.target.value)} /><button type="button" className="btn-primary h-9 text-sm" disabled={!editingTagName.trim() || updateTag.isPending || deleteTag.isPending} onClick={() => void saveEditedTag()}>{updateTag.isPending ? "保存中…" : "保存标签"}</button><button type="button" className="btn-ghost h-9 text-sm text-red-600 hover:bg-red-50" disabled={updateTag.isPending || deleteTag.isPending} onClick={() => void removeEditedTag()}>{deleteTag.isPending ? "删除中…" : "删除"}</button></div>{editingTagError && <p className="mt-2 text-xs text-red-600">{editingTagError}</p>}</div>}
        <PaperFolderSelector folders={folders.data ?? []} selectedIds={folderIds} disabled={disabled} onChange={setFolderIds} />
      </div></div>
      <div className="flex items-center justify-between gap-2 border-t border-gray-200 px-6 py-4 dark:border-slate-700"><div>{onDelete && <button type="button" className="btn-ghost inline-flex items-center gap-2 text-red-600 hover:bg-red-50 hover:text-red-700 dark:hover:bg-red-950/30" disabled={disabled} onClick={() => void handleDelete()}><Trash2 className="h-4 w-4" />{isDeleting ? "删除中…" : "删除论文"}</button>}</div><div className="flex items-center gap-2"><button type="button" className="btn-ghost" disabled={disabled} onClick={requestClose}>取消</button><button type="button" className="btn-primary inline-flex items-center gap-2" disabled={disabled} onClick={() => void handleSave()}>{save.isPending && <LoaderCircle className="h-4 w-4 animate-spin" />}{save.isPending ? "保存中…" : "保存"}</button></div></div>
    </div>
  </div>;
}

function Field({ label, value, onChange, disabled, type = "text" }: { label: string; value: string; onChange: (value: string) => void; disabled?: boolean; type?: "text" | "number" }) {
  return <label className="block text-sm"><span className="mb-1 block text-gray-600 dark:text-gray-300">{label}</span><input className="input" type={type} value={value} disabled={disabled} onChange={(event) => onChange(event.target.value)} /></label>;
}
