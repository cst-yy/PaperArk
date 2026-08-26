import { useState } from "react";
import { NavLink, useLocation, useNavigate } from "react-router-dom";
import {
  BookOpen,
  Folder as FolderIcon,
  Brain,
  Settings as SettingsIcon,
  FlaskConical,
  Ellipsis,
  Palette,
  Pencil,
  Plus,
  Trash2,
  X,
  Network,
  BrainCircuit,
  PanelLeftClose,
  PanelLeftOpen,
  TableProperties,
  CircleDollarSign,
} from "lucide-react";
import clsx from "clsx";
import { useFolders, useCreateFolder, useDeleteFolder, useUpdateFolder } from "@/features/folder/hooks";
import { useTags, useCreateTag, useDeleteTag, useUpdateTag } from "@/features/tag/hooks";
import { getStableColor } from "@/utils";
import type { Folder } from "@/features/folder/types";
import type { Tag } from "@/features/tag/types";
import { useUIStore } from "@/stores/uiStore";
import { Popover } from "@/components/overlay";

export function Sidebar() {
  const navigate = useNavigate();
  const location = useLocation();
  const { data: folders } = useFolders();
  const { data: tags } = useTags();
  const createFolderMut = useCreateFolder();
  const updateFolderMut = useUpdateFolder();
  const deleteFolderMut = useDeleteFolder();
  const createTagMut = useCreateTag();
  const updateTagMut = useUpdateTag();
  const deleteTagMut = useDeleteTag();
  const sidebarCollapsed = useUIStore((state) => state.sidebarCollapsed);
  const toggleSidebar = useUIStore((state) => state.toggleSidebar);

  const [newFolderName, setNewFolderName] = useState("");
  const [showFolderInput, setShowFolderInput] = useState(false);
  const [newTagName, setNewTagName] = useState("");
  const [showTagInput, setShowTagInput] = useState(false);
  const [editingTagId, setEditingTagId] = useState<string | null>(null);
  const [editingTagName, setEditingTagName] = useState("");
  const [editingTagColor, setEditingTagColor] = useState("#6366f1");
  const [tagError, setTagError] = useState<string | null>(null);
  const [folderMenuId,setFolderMenuId]=useState<string|null>(null);
  const [editingFolderId,setEditingFolderId]=useState<string|null>(null);
  const [editingFolderName,setEditingFolderName]=useState("");
  const [folderError,setFolderError]=useState<string|null>(null);

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
        <div className="group flex items-center rounded-md text-[13px] text-gray-600 hover:bg-gray-100" style={{ paddingLeft: `${6 + depth * 14}px` }}>{editingFolderId===folder.id?<input autoFocus className="mx-1 h-7 min-w-0 flex-1 rounded border px-1.5 text-xs" value={editingFolderName} onFocus={e=>e.currentTarget.select()} onChange={e=>setEditingFolderName(e.target.value)} onBlur={()=>{const name=editingFolderName.trim();if(name&&name!==folder.name)updateFolderMut.mutate({folderId:folder.id,data:{expected_revision:folder.revision,name}},{onError:()=>setFolderError("文件夹重命名失败"),onSettled:()=>setEditingFolderId(null)});else setEditingFolderId(null);}} onKeyDown={e=>{if(e.key==="Enter")e.currentTarget.blur();if(e.key==="Escape"){setEditingFolderName(folder.name);setEditingFolderId(null);}}}/>:<button onClick={() => handleFolderClick(folder.id)} className="flex min-w-0 flex-1 items-center gap-1.5 px-1.5 py-1.5 text-left"><FolderIcon className="h-3.5 w-3.5 shrink-0" style={{color:folder.color??"#94a3b8"}}/><span className="truncate">{folder.name}</span>{folder.paper_count>0&&<span className="ml-auto text-[11px] text-gray-400">{folder.paper_count}</span>}</button>}<Popover open={folderMenuId===folder.id} onOpenChange={open=>setFolderMenuId(open?folder.id:null)} trigger={props=><button {...props} aria-label={`管理文件夹 ${folder.name}`} className="mr-1 rounded p-1 text-gray-400 opacity-0 hover:bg-gray-200 group-hover:opacity-100 focus:opacity-100"><Ellipsis className="h-3.5 w-3.5"/></button>} contentClassName="absolute left-full top-0 z-40 ml-1 w-44 rounded-lg border bg-white p-2 shadow-xl dark:border-slate-700 dark:bg-slate-900"><button className="block w-full rounded px-2 py-1 text-left text-xs hover:bg-gray-100" onClick={()=>{setEditingFolderId(folder.id);setEditingFolderName(folder.name);setFolderMenuId(null);}}>重命名</button><p className="px-2 pt-2 text-[10px] text-gray-400">更改颜色</p><div className="grid grid-cols-5 gap-1 p-1">{[null,"#94a3b8","#ef4444","#f59e0b","#eab308","#22c55e","#06b6d4","#3b82f6","#8b5cf6","#ec4899"].map(color=><button key={color??"default"} aria-label={color?`文件夹颜色 ${color}`:"默认文件夹颜色"} className="h-5 w-5 rounded-full border" style={{backgroundColor:color??"#e2e8f0"}} onClick={()=>updateFolderMut.mutate({folderId:folder.id,data:{expected_revision:folder.revision,color}},{onSuccess:()=>setFolderMenuId(null),onError:()=>setFolderError("文件夹颜色保存失败")})}/>)}</div><button className="mt-1 flex w-full items-center gap-1 rounded px-2 py-1 text-xs text-red-600 hover:bg-red-50" onClick={()=>{if(confirm(`删除“${folder.name}”？论文不会被删除。`))deleteFolderMut.mutate(folder.id);}}><Trash2 className="h-3.5 w-3.5"/>删除</button></Popover></div>
        {folder.children.length > 0 && renderFolderTree(folder.children, depth + 1)}
      </div>
    ));
  };

  if (sidebarCollapsed) {
    return (
      <aside className="flex h-full w-14 shrink-0 flex-col items-center border-r border-gray-200 bg-white py-3 dark:border-slate-700 dark:bg-slate-900">
        <FlaskConical className="mb-3 h-5 w-5 text-primary-500" />
        <button
          type="button"
          aria-label="展开侧边栏"
          title="展开侧边栏"
          className="rounded-lg p-2 text-gray-500 hover:bg-gray-100 hover:text-gray-800 dark:text-gray-400 dark:hover:bg-slate-800 dark:hover:text-gray-100"
          onClick={toggleSidebar}
        >
          <PanelLeftOpen className="h-5 w-5" />
        </button>
      </aside>
    );
  }

  return (
    <aside className="flex h-full w-60 shrink-0 flex-col border-r border-gray-200 bg-white dark:border-slate-700 dark:bg-slate-900">
      {/* Logo */}
      <div className="flex items-center gap-2 border-b border-gray-100 px-5 py-4 dark:border-slate-700">
        <FlaskConical className="h-5 w-5 text-primary-500" />
        <span className="min-w-0 flex-1 truncate text-sm font-semibold">AI Research Workspace</span>
        <button type="button" aria-label="收起侧边栏" title="收起侧边栏" className="rounded p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-700 dark:hover:bg-slate-800 dark:hover:text-gray-200" onClick={toggleSidebar}>
          <PanelLeftClose className="h-4 w-4" />
        </button>
      </div>

      {/* Nav */}
      <nav className="px-3 py-3 space-y-0.5">
        <NavLink
          to="/"
          end
          className={({ isActive }) =>
            clsx(
              "flex min-h-9 items-center gap-3 rounded-lg px-3 py-2 text-[13px] transition-colors",
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
              "flex min-h-9 items-center gap-3 rounded-lg px-3 py-2 text-[13px] transition-colors",
              isActive
                ? "bg-primary-50 text-primary-600 font-medium"
                : "text-gray-600 hover:bg-gray-50"
            )
          }
        >
          <BookOpen className="h-4 w-4" />
          我的论文
        </NavLink>
        <NavLink to="/papers" className={({ isActive }) => clsx("flex min-h-9 items-center gap-3 rounded-lg px-3 py-2 text-[13px] transition-colors", isActive ? "bg-primary-50 text-primary-600 font-medium" : "text-gray-600 hover:bg-gray-50")}> 
          <TableProperties className="h-4 w-4" />
          论文列表
        </NavLink>
        <NavLink
          to="/notes"
          className={({ isActive }) =>
            clsx(
              "flex min-h-9 items-center gap-3 rounded-lg px-3 py-2 text-[13px] transition-colors",
              isActive
                ? "bg-primary-50 text-primary-600 font-medium"
                : "text-gray-600 hover:bg-gray-50"
            )
          }
        >
          <Brain className="h-4 w-4" />
          笔记
        </NavLink>
        <NavLink
          to="/graph/citations"
          className={({ isActive }) => clsx("flex min-h-9 items-center gap-3 rounded-lg px-3 py-2 text-[13px] transition-colors", isActive ? "bg-primary-50 text-primary-600 font-medium" : "text-gray-600 hover:bg-gray-50")}
        >
          <Network className="h-4 w-4" />
          引用图谱
        </NavLink>
        <NavLink
          to="/graph/knowledge"
          className={({ isActive }) => clsx("flex min-h-9 items-center gap-3 rounded-lg px-3 py-2 text-[13px] transition-colors", isActive ? "bg-primary-50 text-primary-600 font-medium" : "text-gray-600 hover:bg-gray-50")}
        >
          <Network className="h-4 w-4" />
          知识图谱
        </NavLink>
        <NavLink
          to="/mind-map"
          className={({ isActive }) => clsx("flex min-h-9 items-center gap-3 rounded-lg px-3 py-2 text-[13px] transition-colors", isActive ? "bg-primary-50 text-primary-600 font-medium" : "text-gray-600 hover:bg-gray-50")}
        >
          <BrainCircuit className="h-4 w-4" />
          论文思维导图
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
        {folderError&&<p className="px-2 py-1 text-[11px] text-red-600">{folderError}</p>}
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
        <NavLink to="/settings/ai-usage" className={({isActive})=>clsx("sidebar-nav-item",isActive&&"sidebar-nav-item-active")}><CircleDollarSign className="h-4 w-4"/><span>AI 用量与费用</span></NavLink>
        <p className="mt-1 px-3 text-xs text-gray-400">v0.1.0 · S2</p>
      </div>
    </aside>
  );
}
