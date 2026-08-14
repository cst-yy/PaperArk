import { useState } from "react";
import { NavLink, useLocation, useNavigate } from "react-router-dom";
import {
  BookOpen,
  Star,
  Folder as FolderIcon,
  Brain,
  Search,
  Settings as SettingsIcon,
  FlaskConical,
  Ellipsis,
  Palette,
  Pencil,
  Plus,
  Trash2,
  X,
} from "lucide-react";
import clsx from "clsx";
import { useFolders, useCreateFolder } from "@/features/folder/hooks";
import { useTags, useCreateTag, useDeleteTag, useUpdateTag } from "@/features/tag/hooks";
import { getStableColor } from "@/utils";
import type { Folder } from "@/features/folder/types";
import type { Tag } from "@/features/tag/types";

export function Sidebar() {
  const navigate = useNavigate();
  const location = useLocation();
  const { data: folders } = useFolders();
  const { data: tags } = useTags();
  const createFolderMut = useCreateFolder();
  const createTagMut = useCreateTag();
  const updateTagMut = useUpdateTag();
  const deleteTagMut = useDeleteTag();

  const [newFolderName, setNewFolderName] = useState("");
  const [showFolderInput, setShowFolderInput] = useState(false);
  const [newTagName, setNewTagName] = useState("");
  const [showTagInput, setShowTagInput] = useState(false);
  const [editingTagId, setEditingTagId] = useState<string | null>(null);
  const [editingTagName, setEditingTagName] = useState("");
  const [editingTagColor, setEditingTagColor] = useState("#6366f1");
  const [tagError, setTagError] = useState<string | null>(null);

  const handleCreateFolder = async () => {
    if (!newFolderName.trim()) return;
    await createFolderMut.mutateAsync({ name: newFolderName.trim() });
    setNewFolderName("");
    setShowFolderInput(false);
  };

  const handleCreateTag = async () => {
    if (!newTagName.trim()) return;
    await createTagMut.mutateAsync({ name: newTagName.trim() });
    setNewTagName("");
    setShowTagInput(false);
  };

  const handleFolderClick = (folderId: string) => {
    navigate(`/library?folder_id=${folderId}`);
  };

  const handleTagClick = (tagId: string) => {
    navigate(`/library?tag_id=${tagId}`);
  };

  const tagErrorMessage = (error: unknown) => {
    const detail = (error as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail;
    return typeof detail === "string" ? detail : "标签操作失败，请稍后重试。";
  };

  const openTagEditor = (tag: Tag) => {
    setTagError(null);
    setEditingTagId(tag.id);
    setEditingTagName(tag.name);
    setEditingTagColor(tag.color || getStableColor(tag.name));
  };

  const saveTag = async () => {
    if (!editingTagId || !editingTagName.trim()) return;
    setTagError(null);
    try {
      await updateTagMut.mutateAsync({ tagId: editingTagId, data: { name: editingTagName.trim(), color: editingTagColor } });
      setEditingTagId(null);
    } catch (error) {
      setTagError(tagErrorMessage(error));
    }
  };

  const removeTag = async (tagId: string, tagName: string) => {
    if (!window.confirm(`删除“${tagName}”不会删除论文，只会解除论文与该标签的关联。确定删除吗？`)) return;
    setTagError(null);
    try {
      await deleteTagMut.mutateAsync(tagId);
      const params = new URLSearchParams(location.search);
      if (params.get("tag_id") === tagId) {
        params.delete("tag_id");
        params.delete("page");
        navigate(`/library${params.toString() ? `?${params}` : ""}`);
      }
    } catch (error) {
      setTagError(tagErrorMessage(error));
    }
  };

  const renderFolderTree = (folders: Folder[], depth = 0) => {
    return folders.map((folder) => (
      <div key={folder.id}>
        <button
          onClick={() => handleFolderClick(folder.id)}
          className="flex w-full items-center gap-1.5 rounded-md px-2 py-1 text-sm text-gray-600 hover:bg-gray-100 transition-colors"
          style={{ paddingLeft: `${12 + depth * 16}px` }}
        >
          <FolderIcon className="h-3.5 w-3.5 shrink-0 text-gray-400" />
          <span className="truncate">{folder.name}</span>
          {folder.paper_count > 0 && (
            <span className="ml-auto text-xs text-gray-400">{folder.paper_count}</span>
          )}
        </button>
        {folder.children.length > 0 && renderFolderTree(folder.children, depth + 1)}
      </div>
    ));
  };

  return (
    <aside className="flex w-60 flex-col border-r border-gray-200 bg-white">
      {/* Logo */}
      <div className="flex items-center gap-2 px-5 py-4 border-b border-gray-100">
        <FlaskConical className="h-5 w-5 text-primary-500" />
        <span className="text-sm font-semibold">AI Research Workspace</span>
      </div>

      {/* Nav */}
      <nav className="px-3 py-3 space-y-0.5">
        <NavLink
          to="/"
          end
          className={({ isActive }) =>
            clsx(
              "flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition-colors",
              isActive
                ? "bg-primary-50 text-primary-600 font-medium"
                : "text-gray-600 hover:bg-gray-50"
            )
          }
        >
          <BookOpen className="h-4 w-4" />
          仪表盘
        </NavLink>
        <NavLink
          to="/library"
          className={({ isActive }) =>
            clsx(
              "flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition-colors",
              isActive
                ? "bg-primary-50 text-primary-600 font-medium"
                : "text-gray-600 hover:bg-gray-50"
            )
          }
        >
          <BookOpen className="h-4 w-4" />
          我的论文
        </NavLink>
        <NavLink
          to="/library?starred=true"
          className="flex items-center gap-3 rounded-lg px-3 py-2 text-sm text-gray-600 hover:bg-gray-50 transition-colors"
        >
          <Star className="h-4 w-4" />
          收藏
        </NavLink>
        <NavLink
          to="/search"
          className={({ isActive }) =>
            clsx(
              "flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition-colors",
              isActive
                ? "bg-primary-50 text-primary-600 font-medium"
                : "text-gray-600 hover:bg-gray-50"
            )
          }
        >
          <Search className="h-4 w-4" />
          全文搜索
        </NavLink>
        <NavLink
          to="/notes"
          className={({ isActive }) =>
            clsx(
              "flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition-colors",
              isActive
                ? "bg-primary-50 text-primary-600 font-medium"
                : "text-gray-600 hover:bg-gray-50"
            )
          }
        >
          <Brain className="h-4 w-4" />
          笔记
        </NavLink>
      </nav>

      {/* Folders */}
      <div className="border-t border-gray-100 px-3 py-2">
        <div className="flex items-center justify-between px-2 py-1">
          <span className="text-xs font-medium text-gray-400 uppercase tracking-wide">文件夹</span>
          <button
            onClick={() => setShowFolderInput(!showFolderInput)}
            className="rounded p-0.5 text-gray-400 hover:bg-gray-100 hover:text-gray-600"
          >
            <Plus className="h-3.5 w-3.5" />
          </button>
        </div>

        {showFolderInput && (
          <div className="mb-1 flex items-center gap-1 px-2">
            <input
              type="text"
              autoFocus
              value={newFolderName}
              onChange={(e) => setNewFolderName(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") handleCreateFolder();
                if (e.key === "Escape") setShowFolderInput(false);
              }}
              placeholder="文件夹名称"
              className="w-full rounded border border-gray-200 px-2 py-1 text-xs outline-none focus:border-primary-400"
            />
          </div>
        )}

        <div className="space-y-0.5">
          {folders && renderFolderTree(folders)}
        </div>
      </div>

      {/* Tags */}
      <div className="border-t border-gray-100 px-3 py-2 flex-1 overflow-y-auto">
        <div className="flex items-center justify-between px-2 py-1">
          <span className="text-xs font-medium text-gray-400 uppercase tracking-wide">标签</span>
          <button
            onClick={() => setShowTagInput(!showTagInput)}
            className="rounded p-0.5 text-gray-400 hover:bg-gray-100 hover:text-gray-600"
          >
            <Plus className="h-3.5 w-3.5" />
          </button>
        </div>

        {showTagInput && (
          <div className="mb-1 flex items-center gap-1 px-2">
            <input
              type="text"
              autoFocus
              value={newTagName}
              onChange={(e) => setNewTagName(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") handleCreateTag();
                if (e.key === "Escape") setShowTagInput(false);
              }}
              placeholder="标签名称"
              className="w-full rounded border border-gray-200 px-2 py-1 text-xs outline-none focus:border-primary-400"
            />
          </div>
        )}

        {tagError && <p className="mb-2 px-2 text-xs text-red-600">{tagError}</p>}
        <div className="space-y-0.5">
          {tags?.map((tag) => (
            <div key={tag.id} className="group flex items-center rounded-md text-sm text-gray-600 hover:bg-gray-100">
              <button onClick={() => handleTagClick(tag.id)} className="flex min-w-0 flex-1 items-center gap-1.5 px-2 py-1 text-left"><span className="h-2.5 w-2.5 shrink-0 rounded-full" style={{ backgroundColor: tag.color || getStableColor(tag.name) }} /><span className="truncate">{tag.name}</span>{tag.paper_count > 0 && <span className="ml-auto text-xs text-gray-400">{tag.paper_count}</span>}</button>
              <button type="button" aria-label={`管理标签 ${tag.name}`} className="mr-1 rounded p-1 text-gray-400 opacity-0 hover:bg-gray-200 hover:text-gray-700 group-hover:opacity-100" onClick={() => openTagEditor(tag)}><Ellipsis className="h-3.5 w-3.5" /></button>
            </div>
          ))}
        </div>
        {editingTagId && <div className="mt-3 space-y-2 rounded-lg border border-gray-200 bg-gray-50 p-2 dark:border-slate-700 dark:bg-slate-800"><div className="flex items-center justify-between"><span className="text-xs font-medium">管理标签</span><button type="button" aria-label="关闭标签编辑" onClick={() => setEditingTagId(null)}><X className="h-3.5 w-3.5" /></button></div><input className="input h-8 text-xs" value={editingTagName} onChange={(event) => setEditingTagName(event.target.value)} placeholder="标签名称" /><div className="flex items-center gap-2"><Palette className="h-3.5 w-3.5 text-gray-500" /><input type="color" value={editingTagColor} onChange={(event) => setEditingTagColor(event.target.value)} className="h-7 w-10 cursor-pointer rounded border-0 bg-transparent p-0" /><button type="button" className="btn-ghost ml-auto h-8 text-xs" disabled={updateTagMut.isPending || !editingTagName.trim()} onClick={() => void saveTag()}><Pencil className="h-3.5 w-3.5" />保存</button></div><button type="button" className="flex w-full items-center justify-center gap-1 rounded border border-red-200 px-2 py-1.5 text-xs text-red-600 hover:bg-red-50" disabled={deleteTagMut.isPending} onClick={() => { const tag = tags?.find((item) => item.id === editingTagId); if (tag) void removeTag(tag.id, tag.name); }}><Trash2 className="h-3.5 w-3.5" />删除标签</button></div>}
      </div>

      {/* Settings */}
      <div className="border-t border-gray-100 px-3 py-2">
        <NavLink
          to="/settings"
          className={({ isActive }) =>
            clsx(
              "flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition-colors",
              isActive
                ? "bg-primary-50 text-primary-600 font-medium"
                : "text-gray-600 hover:bg-gray-50"
            )
          }
        >
          <SettingsIcon className="h-4 w-4" />
          设置
        </NavLink>
        <p className="mt-1 px-3 text-xs text-gray-400">v0.1.0 · S2</p>
      </div>
    </aside>
  );
}
