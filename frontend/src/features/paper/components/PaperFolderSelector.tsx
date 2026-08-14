import { ChevronDown, ChevronRight } from "lucide-react";
import { useState } from "react";

import type { Folder } from "@/features/folder/types";

interface PaperFolderSelectorProps {
  folders: Folder[];
  selectedIds: string[];
  disabled?: boolean;
  onChange: (ids: string[]) => void;
}

export function PaperFolderSelector({ folders, selectedIds, disabled, onChange }: PaperFolderSelectorProps) {
  return <section className="space-y-3"><h3 className="text-sm font-semibold">文件夹</h3><div className="rounded-lg border border-gray-200 p-2 dark:border-slate-700">{folders.length === 0 ? <p className="px-2 py-1 text-xs text-gray-500">暂无文件夹。</p> : folders.map((folder) => <FolderRow key={folder.id} folder={folder} selectedIds={selectedIds} disabled={disabled} onChange={onChange} />)}</div></section>;
}

function FolderRow({ folder, selectedIds, disabled, onChange }: { folder: Folder; selectedIds: string[]; disabled?: boolean; onChange: (ids: string[]) => void }) {
  const [expanded, setExpanded] = useState(true);
  const selected = selectedIds.includes(folder.id);
  const toggle = () => onChange(selected ? selectedIds.filter((id) => id !== folder.id) : [...selectedIds, folder.id]);
  return <div><div className="flex items-center gap-1 rounded px-1 py-1.5 hover:bg-gray-50 dark:hover:bg-slate-800"><button type="button" className="btn-ghost p-0.5" aria-label={expanded ? "收起子文件夹" : "展开子文件夹"} disabled={!folder.children.length} onClick={() => setExpanded((value) => !value)}>{folder.children.length ? (expanded ? <ChevronDown className="h-3.5 w-3.5" /> : <ChevronRight className="h-3.5 w-3.5" />) : <span className="block h-3.5 w-3.5" />}</button><input type="checkbox" checked={selected} disabled={disabled} onChange={toggle} /><span className="ml-1 text-sm">{folder.name}</span></div>{expanded && folder.children.length > 0 && <div className="ml-5 border-l border-gray-100 pl-1 dark:border-slate-700">{folder.children.map((child) => <FolderRow key={child.id} folder={child} selectedIds={selectedIds} disabled={disabled} onChange={onChange} />)}</div>}</div>;
}
